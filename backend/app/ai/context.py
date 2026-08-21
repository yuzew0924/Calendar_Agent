from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from ..models import Course, SectionStatus, SectionType
from ..scheduler.time_utils import DayCode


class AIContextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AIMeetingContext(AIContextModel):
    days: tuple[DayCode, ...]
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")


class AISectionContext(AIContextModel):
    id: str
    type: SectionType
    status: SectionStatus
    meetings: tuple[AIMeetingContext, ...]


class AICourseContext(AIContextModel):
    course_code: str = Field(alias="courseCode")
    title: str | None
    sections: tuple[AISectionContext, ...]


class AICourseCatalogContext(AIContextModel):
    courses: tuple[AICourseContext, ...]


def build_ai_course_context(courses: Sequence[Course]) -> AICourseCatalogContext:
    """Build the minimal allowlisted course catalog sent to the AI service."""
    if not courses:
        raise ValueError("at least one course is required for AI preference parsing")

    return AICourseCatalogContext(
        courses=tuple(
            AICourseContext(
                courseCode=course.code,
                title=course.title,
                sections=tuple(
                    AISectionContext(
                        id=section.id,
                        type=group.type,
                        status=section.status,
                        meetings=tuple(
                            AIMeetingContext(
                                days=tuple(meeting.days),
                                startTime=meeting.start_time.strftime("%H:%M"),
                                endTime=meeting.end_time.strftime("%H:%M"),
                            )
                            for meeting in section.meetings
                        ),
                    )
                    for group in course.groups
                    for section in group.sections
                ),
            )
            for course in courses
        )
    )
