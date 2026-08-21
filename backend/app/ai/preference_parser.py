from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from ..models import ParsedPreferences
from .client import AIInvalidResponseError
from .prompts import PREFERENCE_PARSER_INSTRUCTIONS


class TextGenerationClient(Protocol):
    async def generate_text(self, *, instructions: str, input_text: str) -> str: ...


class PreferenceParser:
    """Parse natural language through AI, then validate before returning data."""

    def __init__(self, client: TextGenerationClient) -> None:
        self.client = client

    async def parse(self, preference_text: str) -> ParsedPreferences:
        text = preference_text.strip()
        if not text:
            raise ValueError("preference text must not be empty")

        output = await self.client.generate_text(
            instructions=PREFERENCE_PARSER_INSTRUCTIONS,
            input_text=text,
        )
        try:
            return ParsedPreferences.model_validate_json(output)
        except ValidationError as error:
            raise AIInvalidResponseError(
                "AI response did not match the preference schema"
            ) from error
