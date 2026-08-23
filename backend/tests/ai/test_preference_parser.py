import asyncio
import json
from typing import Any

import pytest

from app.ai.client import AIInvalidResponseError
from app.ai.preference_parser import (
    AIPreferenceConflictError,
    PreferenceParser,
    build_section_index,
    validate_and_convert_preferences,
)
from app.models import Course, ParsedPreferences


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
            "earliestStart": "09:00",
            "earliestStartIsHard": true,
            "preferredDaysOff": ["F"],
            "requiredDaysOff": [],
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
        "```json\n{}\n```",
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


def test_section_index_groups_sections_by_real_course() -> None:
    index = build_section_index(course_catalog())

    assert set(index) == {"CSE 373"}
    assert set(index["CSE 373"]) == {"A", "B"}


def test_grounded_conversion_returns_scheduler_fixed_section_format() -> None:
    parsed = ParsedPreferences.model_validate(
        {"fixedSections": ["CSE 373 A"], "requireOpenSections": True}
    )

    preferences = validate_and_convert_preferences(parsed, course_catalog())

    assert preferences.fixed_sections == {"CSE 373": ["A"]}


@pytest.mark.parametrize("reference", ["CSE 999 A", "CSE 373 ZZ"])
def test_grounded_conversion_rejects_invented_references(reference: str) -> None:
    parsed = ParsedPreferences.model_validate({"fixedSections": [reference]})

    with pytest.raises(ValueError, match="does not exist"):
        validate_and_convert_preferences(parsed, course_catalog())


def test_vague_preference_output_does_not_create_hard_start_time() -> None:
    parser = PreferenceParser(
        FakeAIClient(
            """{
                "earliestStart": null,
                "earliestStartIsHard": false,
                "preferredDaysOff": ["F"],
                "requiredDaysOff": [],
                "fixedSections": [],
                "requireOpenSections": true,
                "hardConstraints": [],
                "softPreferences": ["Avoid classes that are too early"],
                "conflicts": [],
                "needsClarification": false,
                "clarificationQuestions": []
            }"""
        )
    )

    parsed = asyncio.run(
        parser.parse("Not too early; preferably Friday off", course_catalog())
    )
    scheduler_preferences = validate_and_convert_preferences(parsed, course_catalog())

    assert parsed.soft_preferences == ["Avoid classes that are too early"]
    assert scheduler_preferences.earliest_start is None
    assert scheduler_preferences.fixed_sections == {}


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "fixedSections": ["CSE 373 A"],
                "requiredDaysOff": ["M"],
            },
            "required day",
        ),
        (
            {
                "fixedSections": ["CSE 373 A"],
                "earliestStart": "10:00",
                "earliestStartIsHard": True,
            },
            "starts before",
        ),
        (
            {
                "fixedSections": ["CSE 373 A", "CSE 373 B"],
                "requireOpenSections": False,
            },
            "mutually exclusive",
        ),
    ],
)
def test_backend_detects_fixed_section_conflicts(
    payload: dict[str, object],
    message: str,
) -> None:
    parsed = ParsedPreferences.model_validate(payload)

    with pytest.raises(AIPreferenceConflictError, match=message):
        validate_and_convert_preferences(parsed, course_catalog())


def test_ai_reported_conflict_stops_before_scheduler_conversion() -> None:
    parsed = ParsedPreferences.model_validate(
        {
            "conflicts": ["Friday is both required off and required for class"],
            "needsClarification": True,
            "clarificationQuestions": ["Which Friday requirement should change?"],
        }
    )

    with pytest.raises(AIPreferenceConflictError, match="Which Friday requirement"):
        validate_and_convert_preferences(parsed, course_catalog())


def test_malformed_ai_output_never_reaches_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conversion_called = False

    def fail_if_called(*args: object, **kwargs: object) -> None:
        del args, kwargs
        nonlocal conversion_called
        conversion_called = True

    monkeypatch.setattr(
        "app.ai.preference_parser.validate_and_convert_preferences",
        fail_if_called,
    )

    with pytest.raises(AIInvalidResponseError):
        asyncio.run(
            PreferenceParser(FakeAIClient("```json\n{}\n```")).parse(
                "Prefer Friday off",
                course_catalog(),
            )
        )

    assert not conversion_called
