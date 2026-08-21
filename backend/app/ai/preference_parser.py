from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Protocol

from pydantic import ValidationError

from ..models import Course, ParsedPreferences, ScheduleRequest
from .client import AIInvalidResponseError
from .context import build_ai_course_context
from .prompts import PREFERENCE_PARSER_INSTRUCTIONS


class TextGenerationClient(Protocol):
    async def generate_text(self, *, instructions: str, input_text: str) -> str: ...


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
        )
        try:
            parsed = ParsedPreferences.model_validate_json(output)
        except ValidationError as error:
            raise AIInvalidResponseError(
                "AI response did not match the preference schema"
            ) from error

        try:
            ScheduleRequest(
                courses=list(courses),
                preferences=parsed.to_scheduler_preferences(),
            )
        except ValidationError as error:
            raise AIInvalidResponseError(
                "AI response referenced an unavailable course or section"
            ) from error

        return parsed
