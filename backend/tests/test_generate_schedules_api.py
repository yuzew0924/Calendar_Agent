from typing import Any

from fastapi.testclient import TestClient

from app.ai.client import AIRequestTimeoutError
from app.main import app
from app.models import GenerateSchedulesApiResponse


def courses() -> list[dict[str, object]]:
    return [
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
                                    "days": ["M"],
                                    "startTime": "09:30",
                                    "endTime": "10:20",
                                }
                            ],
                        },
                        {
                            "id": "B",
                            "status": "open",
                            "meetings": [
                                {
                                    "days": ["M"],
                                    "startTime": "13:30",
                                    "endTime": "14:20",
                                }
                            ],
                        },
                    ],
                }
            ],
        }
    ]


def parsed_request(**overrides: Any) -> dict[str, object]:
    payload: dict[str, object] = {
        "courses": courses(),
        "preferences": {
            "preferredTimeOfDay": "afternoon",
            "requireOpenSections": True,
        },
        "topN": 1,
        "enhanceReasons": False,
    }
    payload.update(overrides)
    return payload


def test_generate_endpoint_returns_ranked_top_n_and_valid_schema() -> None:
    response = TestClient(app).post(
        "/api/schedules/generate",
        json=parsed_request(),
    )

    assert response.status_code == 200
    body = response.json()
    validated = GenerateSchedulesApiResponse.model_validate(body)
    assert validated.count == 1
    assert len(validated.schedules) == 1
    schedule = body["schedules"][0]
    assert schedule["rank"] == 1
    assert isinstance(schedule["score"], (int, float))
    assert schedule["sections"][0]["sectionId"] == "B"
    assert set(schedule["scoreBreakdown"]) == {
        "earliestStart",
        "preferredTimeOfDay",
        "gaps",
        "preferredDaysOff",
    }
    assert isinstance(schedule["reasons"], list)
    assert isinstance(schedule["tradeoffs"], list)


def test_generate_endpoint_returns_stable_empty_result() -> None:
    response = TestClient(app).post(
        "/api/schedules/generate",
        json=parsed_request(
            preferences={
                "requiredDaysOff": ["M"],
                "requireOpenSections": True,
            }
        ),
    )

    assert response.status_code == 200
    assert response.json()["schedules"] == []
    assert response.json()["count"] == 0
    assert response.json()["warnings"] == [
        "Hard day-off or earliest-start constraints eliminate the remaining combinations.",
        "All remaining combinations have meeting conflicts or incompatible course-component requirements.",
    ]


def test_parser_failure_stops_before_scheduler(
    monkeypatch: Any,
) -> None:
    scheduler_called = False

    class FailingParser:
        async def parse(self, *args: Any, **kwargs: Any) -> None:
            del args, kwargs
            raise AIRequestTimeoutError("AI request timed out")

    def fail_if_called(*args: Any, **kwargs: Any) -> tuple[()]:
        del args, kwargs
        nonlocal scheduler_called
        scheduler_called = True
        return ()

    monkeypatch.setattr("app.main.get_preference_parser", lambda: FailingParser())
    monkeypatch.setattr("app.generation.generate_schedule_candidates", fail_if_called)
    response = TestClient(app).post(
        "/api/schedules/generate",
        json={
            "courses": courses(),
            "preferenceText": "Prefer afternoon classes",
            "enhanceReasons": False,
        },
    )

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_request_timeout"
    assert not scheduler_called


def test_reason_ai_failure_uses_deterministic_reasons(monkeypatch: Any) -> None:
    class InvalidReasonClient:
        async def generate_text(self, **request: Any) -> str:
            del request
            return "not json"

    monkeypatch.setattr("app.main.get_ai_client", lambda: InvalidReasonClient())
    response = TestClient(app).post(
        "/api/schedules/generate",
        json=parsed_request(enhanceReasons=True),
    )

    assert response.status_code == 200
    assert "No time conflicts" in response.json()["schedules"][0]["reasons"]
