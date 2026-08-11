import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.models import GenerateScheduleRequest, GenerateScheduleResponse, Meeting


SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "sample-data" / "courses.json"


@pytest.fixture
def sample_request_data() -> dict[str, object]:
    return json.loads(SAMPLE_DATA_PATH.read_text())


def test_sample_data_matches_request_model(sample_request_data: dict[str, object]) -> None:
    request = GenerateScheduleRequest.model_validate(sample_request_data)

    assert len(request.courses) == 2
    assert request.preferences.earliest_start is not None
    assert request.max_results == 10
    assert request.model_dump(mode="json", by_alias=True)["maxResults"] == 10


def test_request_schema_uses_documented_json_names() -> None:
    properties = GenerateScheduleRequest.model_json_schema(by_alias=True)["properties"]

    assert set(properties) == {"courses", "preferences", "maxResults"}


def test_invalid_meeting_time_is_rejected() -> None:
    with pytest.raises(ValidationError, match="start must be earlier than end"):
        Meeting(days=["M"], start="13:20", end="12:30")


def test_unknown_section_dependency_is_rejected(
    sample_request_data: dict[str, object],
) -> None:
    invalid_request = deepcopy(sample_request_data)
    courses = invalid_request["courses"]
    courses[0]["groups"][1]["sections"][0]["requiredSectionIds"] = ["missing"]

    with pytest.raises(ValidationError, match="requires unknown section missing"):
        GenerateScheduleRequest.model_validate(invalid_request)


def test_generate_response_uses_typed_options() -> None:
    response = GenerateScheduleResponse.model_validate(
        {
            "options": [
                {
                    "id": "option-1",
                    "rank": 1,
                    "score": 94,
                    "selections": [
                        {
                            "courseCode": "CSE 414",
                            "groupId": "lecture",
                            "section": {
                                "id": "C",
                                "status": "open",
                                "meetings": [
                                    {
                                        "days": ["M", "W", "F"],
                                        "start": "12:30",
                                        "end": "13:20",
                                    }
                                ],
                            },
                        }
                    ],
                    "reasons": ["No conflicts"],
                }
            ],
            "totalOptions": 1,
        }
    )

    assert response.options[0].selections[0].course_code == "CSE 414"
    assert response.model_dump(mode="json", by_alias=True)["totalOptions"] == 1


def test_models_can_be_used_as_fastapi_schemas() -> None:
    api = FastAPI()

    @api.post("/generate", response_model=GenerateScheduleResponse)
    def generate_schedules(
        request: GenerateScheduleRequest,
    ) -> GenerateScheduleResponse:
        return GenerateScheduleResponse(options=[], total_options=0)

    operation = api.openapi()["paths"]["/generate"]["post"]
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["responses"]["200"]["content"]["application/json"][
        "schema"
    ]

    assert request_schema["$ref"].endswith("/GenerateScheduleRequest")
    assert response_schema["$ref"].endswith("/GenerateScheduleResponse")
