from __future__ import annotations

import re
from datetime import time
from enum import Enum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class DayCode(str, Enum):
    MONDAY = "M"
    TUESDAY = "T"
    WEDNESDAY = "W"
    THURSDAY = "Th"
    FRIDAY = "F"


class SectionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class SectionType(str, Enum):
    LECTURE = "lecture"
    QUIZ = "quiz"
    LAB = "lab"
    DISCUSSION = "discussion"
    OTHER = "other"


class Meeting(APIModel):
    days: list[DayCode] = Field(min_length=1)
    start_time: time
    end_time: time
    location: str | None = None

    @field_validator("days")
    @classmethod
    def validate_unique_days(cls, days: list[DayCode]) -> list[DayCode]:
        if len(days) != len(set(days)):
            raise ValueError("meeting days must not contain duplicates")
        return days

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def validate_time_format(cls, value: object) -> object:
        if isinstance(value, str) and TIME_PATTERN.fullmatch(value) is None:
            raise ValueError("time must use 24-hour HH:MM format")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("startTime must be earlier than endTime")
        return self

    @field_serializer("start_time", "end_time", when_used="json")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")


class Section(APIModel):
    id: str = Field(min_length=1)
    type: SectionType
    status: SectionStatus
    sln: str | None = None
    meetings: list[Meeting]
    required_section_ids: list[str] = Field(default_factory=list)

    @field_validator("required_section_ids")
    @classmethod
    def validate_required_section_ids(cls, section_ids: list[str]) -> list[str]:
        if any(not section_id for section_id in section_ids):
            raise ValueError("required section IDs must not be empty")
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("required section IDs must not contain duplicates")
        return section_ids

    @model_validator(mode="after")
    def validate_no_self_dependency(self) -> Self:
        if self.id in self.required_section_ids:
            raise ValueError("a section cannot require itself")
        return self


class SectionGroup(APIModel):
    type: SectionType
    choose: int = Field(ge=0)
    sections: list[Section]

    @model_validator(mode="after")
    def validate_group(self) -> Self:
        if self.choose > len(self.sections):
            raise ValueError("choose cannot exceed the number of sections")
        if any(section.type is not self.type for section in self.sections):
            raise ValueError("every section type must match its group type")
        return self


class Course(APIModel):
    course_code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section_groups: list[SectionGroup] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_groups_and_dependencies(self) -> Self:
        group_types = [group.type for group in self.section_groups]
        if len(group_types) != len(set(group_types)):
            raise ValueError("section group types must be unique within a course")

        sections: dict[str, Section] = {}
        section_types: dict[str, SectionType] = {}
        for group in self.section_groups:
            for section in group.sections:
                if section.id in sections:
                    raise ValueError("section IDs must be unique within a course")
                sections[section.id] = section
                section_types[section.id] = section.type

        for section in sections.values():
            for required_id in section.required_section_ids:
                if required_id not in sections:
                    raise ValueError(
                        f"section {section.id} requires unknown section {required_id}"
                    )
                if section_types[required_id] is section.type:
                    raise ValueError("section dependencies must reference another group")

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(section_id: str) -> None:
            if section_id in visiting:
                raise ValueError("section dependencies must not contain cycles")
            if section_id in visited:
                return

            visiting.add(section_id)
            for required_id in sections[section_id].required_section_ids:
                visit(required_id)
            visiting.remove(section_id)
            visited.add(section_id)

        for section_id in sections:
            visit(section_id)

        return self


class Preferences(APIModel):
    earliest_start: time | None = None
    allow_earlier_if_only_option: bool = False
    allowed_gap_minutes: list[int] = Field(default_factory=list)
    minimum_long_gap_minutes: int | None = Field(default=None, ge=0)
    require_open_sections: bool = True
    fixed_sections: list[str] = Field(default_factory=list)

    @field_validator("earliest_start", mode="before")
    @classmethod
    def validate_earliest_start_format(cls, value: object) -> object:
        if isinstance(value, str) and TIME_PATTERN.fullmatch(value) is None:
            raise ValueError("time must use 24-hour HH:MM format")
        return value

    @field_validator("allowed_gap_minutes")
    @classmethod
    def validate_allowed_gaps(cls, gaps: list[int]) -> list[int]:
        if any(gap < 0 for gap in gaps):
            raise ValueError("allowed gap minutes must be non-negative")
        if len(gaps) != len(set(gaps)):
            raise ValueError("allowed gap minutes must not contain duplicates")
        return gaps

    @field_validator("fixed_sections")
    @classmethod
    def validate_fixed_sections(cls, fixed_sections: list[str]) -> list[str]:
        if any(not section for section in fixed_sections):
            raise ValueError("fixed sections must not be empty")
        if len(fixed_sections) != len(set(fixed_sections)):
            raise ValueError("fixed sections must not contain duplicates")
        return fixed_sections

    @field_serializer("earliest_start", when_used="json")
    def serialize_earliest_start(self, value: time | None) -> str | None:
        return value.strftime("%H:%M") if value is not None else None


class GenerateScheduleRequest(APIModel):
    courses: list[Course] = Field(min_length=1)
    preferences: Preferences = Field(default_factory=Preferences)
    max_results: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_courses_and_fixed_sections(self) -> Self:
        course_codes = [course.course_code for course in self.courses]
        if len(course_codes) != len(set(course_codes)):
            raise ValueError("course codes must be unique within a request")

        available_sections: dict[str, Section] = {}
        for course in self.courses:
            for group in course.section_groups:
                for section in group.sections:
                    available_sections[f"{course.course_code} {section.id}"] = section

        for fixed_section in self.preferences.fixed_sections:
            section = available_sections.get(fixed_section)
            if section is None:
                raise ValueError(f"fixed section does not exist: {fixed_section}")
            if (
                self.preferences.require_open_sections
                and section.status is not SectionStatus.OPEN
            ):
                raise ValueError(
                    f"fixed section must be open when requireOpenSections is true: "
                    f"{fixed_section}"
                )

        return self


class SelectedSection(APIModel):
    course_code: str = Field(min_length=1)
    group_type: SectionType
    section: Section


class ScheduleOption(APIModel):
    id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    score: float = Field(ge=0, le=100)
    selections: list[SelectedSection] = Field(min_length=1)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GenerateScheduleResponse(APIModel):
    options: list[ScheduleOption]
    total_options: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_options(self) -> Self:
        if self.total_options < len(self.options):
            raise ValueError("total options cannot be smaller than returned options")

        option_ids = [option.id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("schedule option IDs must be unique")

        expected_ranks = list(range(1, len(self.options) + 1))
        if [option.rank for option in self.options] != expected_ranks:
            raise ValueError("schedule options must be ordered with consecutive ranks")

        return self
