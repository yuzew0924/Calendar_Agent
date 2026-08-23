import json
from typing import Any

import httpx
from fastapi.testclient import TestClient
from openai import APITimeoutError

from app.ai.client import AIClient, AIClientSettings
from app.ai.preference_parser import PreferenceParser
from app.main import app, get_preference_parser


class FakeResponses:
    def __init__(self, *, output: str | None = None, error: Exception | None = None) -> None:
        self.output = output
        self.error = error
        self.calls = 0

    async def create(self, **request: Any) -> Any:
        del request
        self.calls += 1
        if self.error is not None:
            raise self.error
        return type("Response", (), {"output_text": self.output})()


class FakeSDKClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def request_body() -> dict[str, object]:
    return {
        "courses": [
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
                                        "startTime": "10:30",
                                        "endTime": "11:20",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "preferenceText": "Prefer Friday off, but CSE 373 A is required.",
    }


def parser_for(responses: FakeResponses) -> PreferenceParser:
    client = AIClient(
        AIClientSettings(
            api_key="test-key",
            model="test-model",
            timeout_seconds=20,
        ),
        sdk_client=FakeSDKClient(responses),
    )
    return PreferenceParser(client)


def test_parse_preferences_endpoint_returns_validated_preferences() -> None:
    responses = FakeResponses(
        output=json.dumps(
            {
                "earliestStart": None,
                "earliestStartIsHard": False,
                "preferredDaysOff": ["F"],
                "requiredDaysOff": [],
                "fixedSections": ["CSE 373 A"],
                "requireOpenSections": True,
                "hardConstraints": ["Fixed section: CSE 373 A"],
                "softPreferences": ["Prefer Friday off"],
                "conflicts": [],
                "needsClarification": False,
                "clarificationQuestions": [],
            }
        )
    )
    app.dependency_overrides[get_preference_parser] = lambda: parser_for(responses)

    try:
        response = TestClient(app).post("/parse-preferences", json=request_body())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["fixedSections"] == ["CSE 373 A"]
    assert response.json()["preferredDaysOff"] == ["F"]
    assert responses.calls == 1


def test_parse_preferences_endpoint_returns_validation_error() -> None:
    responses = FakeResponses(output="{}")
    app.dependency_overrides[get_preference_parser] = lambda: parser_for(responses)

    try:
        response = TestClient(app).post(
            "/parse-preferences",
            json={"courses": [], "preferenceText": ""},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert responses.calls == 0


def test_parse_preferences_timeout_returns_stable_error() -> None:
    responses = FakeResponses(
        error=APITimeoutError(httpx.Request("POST", "https://api.openai.com"))
    )
    app.dependency_overrides[get_preference_parser] = lambda: parser_for(responses)

    try:
        response = TestClient(app).post("/parse-preferences", json=request_body())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_request_timeout"
    assert responses.calls == 1


def test_parse_preferences_invalid_ai_json_returns_stable_error() -> None:
    responses = FakeResponses(output="not json")
    app.dependency_overrides[get_preference_parser] = lambda: parser_for(responses)

    try:
        response = TestClient(app).post("/parse-preferences", json=request_body())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_invalid_response"
