import asyncio
import json
from typing import Any

import pytest

from app.ai.client import AIInvalidResponseError
from app.ai.preference_parser import PreferenceParser
from app.models import Course


class FakeAIClient:
    def __init__(self, output: str) -> None:
        self.output = output
        self.instructions: str | None = None
        self.input_text: str | None = None
        self.response_schema: dict[str, Any] | None = None
        self.response_schema_name: str | None = None

    async def generate_text(
        self,
        *,
        instructions: str,
        input_text: str,
        response_schema: dict[str, Any] | None = None,
        response_schema_name: str = "structured_response",
    ) -> str:
        self.instructions = instructions
        self.input_text = input_text
        self.response_schema = response_schema
        self.response_schema_name = response_schema_name
        return self.output


def course_catalog() -> list[Course]:
    return [
        Course.model_validate(
            {
                "code": "CSE 373",
                "title": "Data Structures and Algorithms",
                "groups": [
                    {
                        "type": "lecture",
                        "sections": [
                            {
                                "id": "A",
                                "status": "open",
                                "meetings": [
                                    {
                                        "days": ["M", "W", "F"],
                                        "startTime": "09:30",
                                        "endTime": "10:20",
                                    }
                                ],
                            },
                            {
                                "id": "B",
                                "status": "closed",
                                "meetings": [],
                            }
                        ],
                    }
                ],
            }
        )
    ]


def test_preference_parser_validates_ai_json() -> None:
    client = FakeAIClient(
        """{
            "earliestStart": "10:00",
            "earliestStartIsHard": true,
            "preferredDaysOff": ["F"],
            "fixedSections": ["CSE 373 A"],
            "requireOpenSections": true,
            "hardConstraints": [],
            "softPreferences": ["Prefer compact schedules"],
            "conflicts": [],
            "needsClarification": false,
            "clarificationQuestions": []
        }"""
    )
    parser = PreferenceParser(client)

    result = asyncio.run(
        parser.parse(
            "No classes before 10 and fix CSE 373 A",
            course_catalog(),
        )
    )

    assert result.earliest_start_is_hard
    assert result.fixed_sections == ["CSE 373 A"]
    assert client.input_text is not None
    sent_payload = json.loads(client.input_text)
    assert sent_payload["preferenceText"] == (
        "No classes before 10 and fix CSE 373 A"
    )
    assert sent_payload["courses"][0]["sections"][0]["id"] == "A"
    assert client.response_schema is not None
    assert client.response_schema["additionalProperties"] is False
    assert client.response_schema_name == "parsed_preferences"


@pytest.mark.parametrize(
    "output",
    [
        "not json",
        '{"earliestStart": "10 AM"}',
        '{"preferredDaysOff": ["Sunday"]}',
        '{"requireOpenSections": "true"}',
        '{"unknownField": true}',
    ],
)
def test_preference_parser_rejects_invalid_ai_output(output: str) -> None:
    parser = PreferenceParser(FakeAIClient(output))

    with pytest.raises(AIInvalidResponseError, match="preference schema"):
        asyncio.run(parser.parse("Prefer Fridays off", course_catalog()))


@pytest.mark.parametrize(
    "fixed_section",
    ["CSE 999 A", "CSE 373 ZZ", "CSE 373 B"],
)
def test_preference_parser_rejects_unavailable_fixed_section(
    fixed_section: str,
) -> None:
    parser = PreferenceParser(
        FakeAIClient(
            f"""{{
                "fixedSections": ["{fixed_section}"],
                "requireOpenSections": true
            }}"""
        )
    )

    with pytest.raises(AIInvalidResponseError, match="unavailable course or section"):
        asyncio.run(parser.parse("Fix a missing section", course_catalog()))


def test_preference_parser_rejects_empty_user_input_before_ai_call() -> None:
    parser = PreferenceParser(FakeAIClient("{}"))

    with pytest.raises(ValueError, match="must not be empty"):
        asyncio.run(parser.parse("   ", course_catalog()))
