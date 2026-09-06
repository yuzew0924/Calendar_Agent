from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..models import Preferences
from ..scheduler.scoring import collect_meeting_facts
from ..scheduler.solver import ScheduleCandidate
from .client import AIClientError
from .preference_parser import TextGenerationClient


REASON_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reasons": {"type": "array", "items": {"type": "string"}},
        "tradeoffs": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["reasons", "tradeoffs"],
}

REASON_WRITER_INSTRUCTIONS = """Rewrite schedule reasons and tradeoffs clearly.
Return one JSON object only, with exactly reasons and tradeoffs arrays.
Preserve the number and meaning of every input item.
Use only facts in scheduleFacts and statements already present in baseReasons or baseTradeoffs.
Do not add courses, sections, weekdays, times, locations, preferences, scores, or rankings.
Do not return Markdown or explanatory text outside the JSON object.
"""

COURSE_PATTERN = re.compile(r"\b[A-Z]{2,4}\s\d{3}\b")
SECTION_REFERENCE_PATTERN = re.compile(
    r"\b([A-Z]{2,4}\s\d{3})\s+(?:section\s+)?([A-Z][A-Z0-9]*)\b"
)
STANDALONE_SECTION_PATTERN = re.compile(r"\bsection\s+([A-Z][A-Z0-9]*)\b")
LOCATION_LIKE_PATTERN = re.compile(r"\b[A-Z]{2,6}\s\d{2,4}\b")
TIME_PATTERN = re.compile(r"\b(?:[01]\d|2[0-3]):[0-5]\d\b")
WEEKDAY_PATTERN = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"
)
DAY_NAMES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "Th": "Thursday",
    "F": "Friday",
}


class RewrittenReasons(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reasons: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)


def build_schedule_facts(
    candidate: ScheduleCandidate,
    preferences: Preferences,
) -> dict[str, object]:
    sections = [
        {
            "courseCode": course.course_code,
            "sectionId": selection.section.id,
            "groupType": selection.group_type.value,
        }
        for course in candidate.courses
        for selection in course.selections
    ]
    meetings = [
        {
            "courseCode": fact.course_code,
            "sectionId": fact.section_id,
            "day": fact.day.value,
            "startTime": fact.start.strftime("%H:%M"),
            "endTime": fact.end.strftime("%H:%M"),
        }
        for fact in collect_meeting_facts(candidate)
    ]
    return {
        "sections": sections,
        "meetings": meetings,
        "preferredDaysOff": [day.value for day in preferences.preferred_days_off],
    }


def _validate_rewrite_facts(
    rewritten: RewrittenReasons,
    candidate: ScheduleCandidate,
    preferences: Preferences,
    base_reasons: Sequence[str],
    base_tradeoffs: Sequence[str],
) -> None:
    if len(rewritten.reasons) != len(base_reasons) or len(
        rewritten.tradeoffs
    ) != len(base_tradeoffs):
        raise ValueError("AI reason rewrite changed the number of explanation items")
    if any(not item for item in (*rewritten.reasons, *rewritten.tradeoffs)):
        raise ValueError("AI reason rewrite contains an empty explanation")

    facts = collect_meeting_facts(candidate)
    allowed_courses = {course.course_code for course in candidate.courses}
    allowed_sections = {
        (course.course_code, selection.section.id)
        for course in candidate.courses
        for selection in course.selections
    }
    allowed_section_ids = {section_id for _, section_id in allowed_sections}
    allowed_times = {
        value.strftime("%H:%M")
        for fact in facts
        for value in (fact.start, fact.end)
    }
    allowed_days = {DAY_NAMES[fact.day.value] for fact in facts} | {
        DAY_NAMES[day.value] for day in preferences.preferred_days_off
    }
    for item in (*rewritten.reasons, *rewritten.tradeoffs):
        if not set(COURSE_PATTERN.findall(item)).issubset(allowed_courses):
            raise ValueError("AI reason rewrite referenced an unknown course")
        if not set(SECTION_REFERENCE_PATTERN.findall(item)).issubset(
            allowed_sections
        ):
            raise ValueError("AI reason rewrite referenced an unknown section")
        if not set(STANDALONE_SECTION_PATTERN.findall(item)).issubset(
            allowed_section_ids
        ):
            raise ValueError("AI reason rewrite referenced an unknown section")
        if not set(TIME_PATTERN.findall(item)).issubset(allowed_times):
            raise ValueError("AI reason rewrite referenced an unknown time")
        if not set(WEEKDAY_PATTERN.findall(item)).issubset(allowed_days):
            raise ValueError("AI reason rewrite referenced an unknown weekday")
        if not set(LOCATION_LIKE_PATTERN.findall(item)).issubset(allowed_courses):
            raise ValueError("AI reason rewrite referenced an unknown location")


class ReasonWriter:
    def __init__(self, client: TextGenerationClient) -> None:
        self.client = client

    async def rewrite_or_fallback(
        self,
        candidate: ScheduleCandidate,
        preferences: Preferences,
        base_reasons: Sequence[str],
        base_tradeoffs: Sequence[str],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        fallback = (tuple(base_reasons), tuple(base_tradeoffs))
        payload = {
            "baseReasons": list(base_reasons),
            "baseTradeoffs": list(base_tradeoffs),
            "scheduleFacts": build_schedule_facts(candidate, preferences),
        }
        try:
            output = await self.client.generate_text(
                instructions=REASON_WRITER_INSTRUCTIONS,
                input_text=json.dumps(payload, separators=(",", ":")),
                response_schema=REASON_RESPONSE_SCHEMA,
                response_schema_name="schedule_reasons",
            )
            rewritten = RewrittenReasons.model_validate_json(output)
            _validate_rewrite_facts(
                rewritten,
                candidate,
                preferences,
                base_reasons,
                base_tradeoffs,
            )
        except (AIClientError, ValidationError, ValueError):
            return fallback
        return tuple(rewritten.reasons), tuple(rewritten.tradeoffs)
