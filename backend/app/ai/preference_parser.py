from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from pydantic import ValidationError

from ..models import Course, ParsedPreferences, Preferences, ScheduleRequest, Section
from .client import AIClientError, AIInvalidResponseError
from .context import build_ai_course_context
from .prompts import PREFERENCE_PARSER_INSTRUCTIONS, PREFERENCE_RESPONSE_SCHEMA


class TextGenerationClient(Protocol):
    async def generate_text(
        self,
        *,
        instructions: str,
        input_text: str,
        response_schema: dict[str, object] | None = None,
        response_schema_name: str = "structured_response",
    ) -> str: ...


SectionIndex = dict[str, dict[str, Section]]


class AIPreferenceConflictError(AIClientError):
    code = "ai_preference_conflict"
    status_code = 409


def build_section_index(courses: Sequence[Course]) -> SectionIndex:
    """Index every real section under its owning course code."""
    return {
        course.code: {
            section.id: section
            for group in course.groups
            for section in group.sections
        }
        for course in courses
    }


def validate_and_convert_preferences(
    parsed: ParsedPreferences,
    courses: Sequence[Course],
) -> Preferences:
    """Ground AI references, then return the scheduler-facing preferences."""
    section_index = build_section_index(courses)
    for reference in parsed.fixed_sections:
        course_code, section_id = reference.rsplit(" ", 1)
        course_sections = section_index.get(course_code)
        if course_sections is None:
            raise ValueError(f"fixed section course does not exist: {course_code}")
        if section_id not in course_sections:
            raise ValueError(f"fixed section does not exist: {course_code} {section_id}")

    conflicts = list(parsed.conflicts)
    fixed_by_course: dict[str, list[str]] = {}
    for reference in parsed.fixed_sections:
        course_code, section_id = reference.rsplit(" ", 1)
        fixed_by_course.setdefault(course_code, []).append(section_id)

    for course in courses:
        fixed_ids = fixed_by_course.get(course.code, [])
        for group in course.groups:
            fixed_in_group = [
                section_id
                for section_id in fixed_ids
                if any(section.id == section_id for section in group.sections)
            ]
            if len(fixed_in_group) > 1:
                conflicts.append(
                    f"{course.code} fixes mutually exclusive {group.type.value} "
                    f"sections: {', '.join(fixed_in_group)}"
                )

    fixed_sections = [
        (course_code, section_index[course_code][section_id])
        for course_code, section_ids in fixed_by_course.items()
        for section_id in section_ids
    ]
    if parsed.earliest_start_is_hard and parsed.earliest_start is not None:
        for course_code, section in fixed_sections:
            if any(
                meeting.start_time < parsed.earliest_start
                for meeting in section.meetings
            ):
                conflicts.append(
                    f"Fixed section {course_code} {section.id} starts before "
                    f"the required earliest time {parsed.earliest_start:%H:%M}"
                )

    required_days_off = set(parsed.required_days_off)
    for course_code, section in fixed_sections:
        conflicting_days = sorted(
            {day.value for meeting in section.meetings for day in meeting.days}
            & {day.value for day in required_days_off}
        )
        if conflicting_days:
            conflicts.append(
                f"Fixed section {course_code} {section.id} meets on required "
                f"day(s) off: {', '.join(conflicting_days)}"
            )

    if conflicts:
        questions = parsed.clarification_questions or [
            "Which conflicting hard requirement should be changed?"
        ]
        raise AIPreferenceConflictError(
            "Preference conflicts require clarification: "
            + "; ".join(dict.fromkeys(conflicts))
            + " Questions: "
            + " ".join(questions)
        )

    preferences = parsed.to_scheduler_preferences()
    ScheduleRequest(courses=list(courses), preferences=preferences)
    return preferences


class PreferenceParser:
    """Parse natural language through AI, then validate before returning data."""

    def __init__(self, client: TextGenerationClient) -> None:
        self.client = client

    async def parse(
        self,
        preference_text: str,
        courses: Sequence[Course],
    ) -> ParsedPreferences:
        text = preference_text.strip()
        if not text:
            raise ValueError("preference text must not be empty")

        context = build_ai_course_context(courses)
        input_payload = {
            "preferenceText": text,
            **context.model_dump(mode="json", by_alias=True),
        }
        output = await self.client.generate_text(
            instructions=PREFERENCE_PARSER_INSTRUCTIONS,
            input_text=json.dumps(input_payload, separators=(",", ":")),
            response_schema=PREFERENCE_RESPONSE_SCHEMA,
            response_schema_name="parsed_preferences",
        )
        try:
            parsed = ParsedPreferences.model_validate_json(output)
        except ValidationError as error:
            raise AIInvalidResponseError(
                "AI response did not match the preference schema"
            ) from error

        try:
            validate_and_convert_preferences(parsed, courses)
        except AIPreferenceConflictError:
            raise
        except (ValidationError, ValueError) as error:
            raise AIInvalidResponseError(
                "AI response referenced an unavailable course or section"
            ) from error

        return parsed
