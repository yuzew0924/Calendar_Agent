from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from .scheduler.time_utils import DayCode, parse_time_string


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
        return parse_time_string(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.start_time >= self.end_time:
            raise ValueError("startTime must be earlier than endTime")
        return self

    @field_serializer("start_time", "end_time", when_used="json")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")


class Section(APIModel):
    id: str = Field(min_length=1, pattern=r"^[A-Z0-9]+$")
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
    choose: Literal[1] = 1
    sections: list[Section]


class Course(APIModel):
    code: str = Field(min_length=1)
    groups: list[SectionGroup] = Field(min_length=1)
    title: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_groups_and_dependencies(self) -> Self:
        group_types = [group.type for group in self.groups]
        if len(group_types) != len(set(group_types)):
            raise ValueError("section group types must be unique within a course")

        sections: dict[str, Section] = {}
        section_types: dict[str, SectionType] = {}
        for group in self.groups:
            for section in group.sections:
                if section.id in sections:
                    raise ValueError("section IDs must be unique within a course")
                sections[section.id] = section
                section_types[section.id] = group.type

        for section in sections.values():
            for required_id in section.required_section_ids:
                if required_id not in sections:
                    raise ValueError(
                        f"section {section.id} requires unknown section {required_id}"
                    )
                if section_types[required_id] is section_types[section.id]:
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
    """Validated preferences consumed by the scheduling engine."""

    earliest_start: time | None = None
    allow_earlier_if_only_option: bool = False
    allowed_gap_minutes: int | None = Field(default=None, ge=0)
    minimum_long_gap_minutes: int | None = Field(default=None, ge=0)
    require_open_sections: bool = True
    fixed_sections: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("earliest_start", mode="before")
    @classmethod
    def validate_earliest_start_format(cls, value: object) -> object:
        return parse_time_string(value) if isinstance(value, str) else value

    @field_validator("fixed_sections")
    @classmethod
    def validate_fixed_sections(
        cls, fixed_sections: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        for course_code, section_ids in fixed_sections.items():
            if not course_code:
                raise ValueError("fixed section course codes must not be empty")
            if not section_ids or any(not section_id for section_id in section_ids):
                raise ValueError("fixed section ID lists must not be empty")
            if len(section_ids) != len(set(section_ids)):
                raise ValueError("fixed section IDs must not contain duplicates")
        return fixed_sections

    @field_serializer("earliest_start", when_used="json")
    def serialize_earliest_start(self, value: time | None) -> str | None:
        return value.strftime("%H:%M") if value is not None else None


class ParsedPreferences(APIModel):
    """Strict structured output accepted from an AI preference parser."""

    earliest_start: time | None = None
    earliest_start_is_hard: bool = False
    preferred_days_off: list[DayCode] = Field(default_factory=list)
    fixed_sections: list[str] = Field(default_factory=list)
    require_open_sections: bool = True
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)

    @field_validator("earliest_start", mode="before")
    @classmethod
    def validate_earliest_start_format(cls, value: object) -> object:
        return parse_time_string(value) if isinstance(value, str) else value

    @field_validator("preferred_days_off")
    @classmethod
    def validate_unique_preferred_days(cls, days: list[DayCode]) -> list[DayCode]:
        if len(days) != len(set(days)):
            raise ValueError("preferredDaysOff must not contain duplicates")
        return days

    @field_validator("fixed_sections")
    @classmethod
    def validate_fixed_section_references(cls, references: list[str]) -> list[str]:
        if len(references) != len(set(references)):
            raise ValueError("fixedSections must not contain duplicates")
        for reference in references:
            try:
                course_code, section_id = reference.rsplit(" ", 1)
            except ValueError as error:
                raise ValueError(
                    "fixedSections entries must use '<course code> <section ID>'"
                ) from error
            if (
                not course_code
                or not section_id.isalnum()
                or section_id != section_id.upper()
            ):
                raise ValueError(
                    "fixedSections entries must use '<course code> <section ID>'"
                )
        return references

    @field_validator("hard_constraints", "soft_preferences")
    @classmethod
    def validate_preference_notes(cls, notes: list[str]) -> list[str]:
        if any(not note for note in notes):
            raise ValueError("preference notes must not be empty")
        if len(notes) != len(set(notes)):
            raise ValueError("preference notes must not contain duplicates")
        return notes

    @model_validator(mode="after")
    def validate_hard_earliest_start(self) -> Self:
        if self.earliest_start_is_hard and self.earliest_start is None:
            raise ValueError("earliestStart is required when earliestStartIsHard is true")
        return self

    @field_serializer("earliest_start", when_used="json")
    def serialize_earliest_start(self, value: time | None) -> str | None:
        return value.strftime("%H:%M") if value is not None else None

    def to_scheduler_preferences(self) -> Preferences:
        """Convert validated AI output into scheduler-safe preferences."""
        fixed_sections: dict[str, list[str]] = {}
        for reference in self.fixed_sections:
            course_code, section_id = reference.rsplit(" ", 1)
            fixed_sections.setdefault(course_code, []).append(section_id)

        return Preferences(
            earliest_start=self.earliest_start,
            allow_earlier_if_only_option=(
                self.earliest_start is not None and not self.earliest_start_is_hard
            ),
            require_open_sections=self.require_open_sections,
            fixed_sections=fixed_sections,
        )


class ScheduleRequest(APIModel):
    courses: list[Course] = Field(min_length=1)
    preferences: Preferences = Field(default_factory=Preferences)

    @model_validator(mode="after")
    def validate_courses_and_fixed_sections(self) -> Self:
        course_codes = [course.code for course in self.courses]
        if len(course_codes) != len(set(course_codes)):
            raise ValueError("course codes must be unique within a request")

        available_sections: dict[str, dict[str, Section]] = {}
        for course in self.courses:
            course_sections: dict[str, Section] = {}
            for group in course.groups:
                for section in group.sections:
                    course_sections[section.id] = section
            available_sections[course.code] = course_sections

        for course_code, section_ids in self.preferences.fixed_sections.items():
            course_sections = available_sections.get(course_code)
            if course_sections is None:
                raise ValueError(f"fixed section course does not exist: {course_code}")

            for section_id in section_ids:
                section = course_sections.get(section_id)
                if section is None:
                    raise ValueError(
                        f"fixed section does not exist: {course_code} {section_id}"
                    )
                if (
                    self.preferences.require_open_sections
                    and section.status is not SectionStatus.OPEN
                ):
                    raise ValueError(
                        "fixed section must be open when requireOpenSections is true: "
                        f"{course_code} {section_id}"
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
    schedules: list[ScheduleOption]
    count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_schedules(self) -> Self:
        if self.count != len(self.schedules):
            raise ValueError("count must equal the number of returned schedules")

        schedule_ids = [schedule.id for schedule in self.schedules]
        if len(schedule_ids) != len(set(schedule_ids)):
            raise ValueError("schedule IDs must be unique")

        expected_ranks = list(range(1, len(self.schedules) + 1))
        if [schedule.rank for schedule in self.schedules] != expected_ranks:
            raise ValueError("schedules must be ordered with consecutive ranks")

        return self


GenerateScheduleRequest = ScheduleRequest
