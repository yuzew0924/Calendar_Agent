import asyncio

import pytest

from app.ai.client import AIInvalidResponseError
from app.ai.preference_parser import PreferenceParser


class FakeAIClient:
    def __init__(self, output: str) -> None:
        self.output = output

    async def generate_text(self, *, instructions: str, input_text: str) -> str:
        del instructions, input_text
        return self.output


def test_preference_parser_validates_ai_json() -> None:
    parser = PreferenceParser(
        FakeAIClient(
            """{
                "earliestStart": "10:00",
                "earliestStartIsHard": true,
                "preferredDaysOff": ["F"],
                "fixedSections": ["CSE 373 A"],
                "requireOpenSections": true,
                "hardConstraints": [],
                "softPreferences": ["Prefer compact schedules"]
            }"""
        )
    )

    result = asyncio.run(parser.parse("No classes before 10 and fix CSE 373 A"))

    assert result.earliest_start_is_hard
    assert result.fixed_sections == ["CSE 373 A"]


def test_preference_parser_rejects_invalid_ai_json() -> None:
    parser = PreferenceParser(FakeAIClient("not json"))

    with pytest.raises(AIInvalidResponseError, match="preference schema"):
        asyncio.run(parser.parse("Prefer Fridays off"))


def test_preference_parser_rejects_empty_user_input_before_ai_call() -> None:
    parser = PreferenceParser(FakeAIClient("{}"))

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(parser.parse("   "))
