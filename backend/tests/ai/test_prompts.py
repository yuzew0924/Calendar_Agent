from app.ai.prompts import (
    PREFERENCE_PARSER_INSTRUCTIONS,
    PREFERENCE_RESPONSE_SCHEMA,
)
from app.models import ParsedPreferences


def test_response_schema_is_strict_complete_and_matches_pydantic_fields() -> None:
    pydantic_properties = set(
        ParsedPreferences.model_json_schema(by_alias=True)["properties"]
    )
    schema_properties = set(PREFERENCE_RESPONSE_SCHEMA["properties"])

    assert PREFERENCE_RESPONSE_SCHEMA["type"] == "object"
    assert PREFERENCE_RESPONSE_SCHEMA["additionalProperties"] is False
    assert schema_properties == pydantic_properties
    assert set(PREFERENCE_RESPONSE_SCHEMA["required"]) == schema_properties


def test_prompt_contains_required_output_and_grounding_rules() -> None:
    prompt = PREFERENCE_PARSER_INSTRUCTIONS

    assert "Do not return Markdown" in prompt
    assert "24-hour HH:MM" in prompt
    assert "M, T, W, Th, or F" in prompt
    assert "Never invent" in prompt
    assert "softPreferences" in prompt
    assert "conflicts" in prompt
    assert "needsClarification" in prompt
    assert "Not too early" in prompt
    assert "Keep earliestStart null" in prompt
    assert "must not start before 10:00" in prompt
    assert "do not invent a value" in prompt
