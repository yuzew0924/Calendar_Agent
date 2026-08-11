import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.models import (
    Course,
    GenerateScheduleRequest,
    GenerateScheduleResponse,
    Meeting,
    Preferences,
    Section,
    SectionGroup,
)


SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "sample-data" / "courses.json"


@pytest.fixture
def sample_request_data() -> dict[str, object]:
    return json.loads(SAMPLE_DATA_PATH.read_text())


def test_meeting_accepts_supported_weekdays() -> None:
    meeting = Meeting.model_validate(
        {
            "days": ["M", "W", "F"],
            "startTime": "09:30",
            "endTime": "10:20",
            "location": "KNE 120",
        }
    )

    assert meeting.model_dump(mode="json", by_alias=True) == {
        "days": ["M", "W", "F"],
        "startTime": "09:30",
        "endTime": "10:20",
        "location": "KNE 120",
    }


@pytest.mark.parametrize("day", ["Monday", "TH", "Sa", "X"])
def test_meeting_rejects_unsupported_weekday(day: str) -> None:
    with pytest.raises(ValidationError):
        Meeting.model_validate(
            {
                "days": [day],
                "startTime": "09:30",
                "endTime": "10:20",
            }
        )


@pytest.mark.parametrize("invalid_time", ["9:30", "09:30:00", "24:00", "09:60"])
def test_meeting_rejects_invalid_time_format(invalid_time: str) -> None:
    with pytest.raises(ValidationError, match="24-hour HH:MM format"):
        Meeting.model_validate(
            {
                "days": ["M"],
                "startTime": invalid_time,
                "endTime": "10:20",
            }
        )


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [("10:20", "10:20"), ("11:20", "10:20")],
)
def test_meeting_rejects_invalid_time_range(start_time: str, end_time: str) -> None:
    with pytest.raises(ValidationError, match="startTime must be earlier than endTime"):
        Meeting.model_validate(
            {
                "days": ["M"],
                "startTime": start_time,
                "endTime": end_time,
            }
        )


def test_section_can_contain_multiple_meetings() -> None:
    section = Section.model_validate(
        {
            "id": "A",
            "type": "lecture",
            "status": "open",
            "sln": "12345",
            "meetings": [
                {
                    "days": ["M", "W"],
                    "startTime": "09:30",
                    "endTime": "10:20",
                },
                {
                    "days": ["F"],
                    "startTime": "11:30",
                    "endTime": "12:20",
                },
            ],
        }
    )

    assert len(section.meetings) == 2


def test_section_group_accepts_valid_choose_count() -> None:
    group = SectionGroup.model_validate(
        {
            "type": "quiz",
            "choose": 1,
            "sections": [
                {
                    "id": "AA",
                    "type": "quiz",
                    "status": "open",
                    "meetings": [],
                }
            ],
        }
    )

    assert group.choose == 1


def test_empty_section_group_allows_choose_zero() -> None:
    group = SectionGroup(type="lab", choose=0, sections=[])

    assert group.sections == []


def test_section_group_rejects_choose_above_section_count() -> None:
    with pytest.raises(ValidationError, match="choose cannot exceed"):
        SectionGroup(type="quiz", choose=1, sections=[])


def test_section_group_rejects_mismatched_section_type() -> None:
    with pytest.raises(ValidationError, match="section type must match"):
        SectionGroup.model_validate(
            {
                "type": "quiz",
                "choose": 1,
                "sections": [
                    {
                        "id": "A",
                        "type": "lecture",
                        "status": "open",
                        "meetings": [],
                    }
                ],
            }
        )


def test_course_can_contain_multiple_section_groups() -> None:
    course = Course.model_validate(
        {
            "courseCode": "CSE 123",
            "title": "Computer Programming III",
            "sectionGroups": [
                {"type": "lecture", "choose": 0, "sections": []},
                {"type": "quiz", "choose": 0, "sections": []},
                {"type": "lab", "choose": 0, "sections": []},
            ],
        }
    )

    assert len(course.section_groups) == 3


def test_preferences_accept_documented_fields() -> None:
    preferences = Preferences.model_validate(
        {
            "earliestStart": "09:30",
            "allowEarlierIfOnlyOption": True,
            "allowedGapMinutes": 90,
            "minimumLongGapMinutes": 120,
            "requireOpenSections": True,
            "fixedSections": {"CSE 123": ["A", "AA"]},
        }
    )

    payload = preferences.model_dump(mode="json", by_alias=True)
    assert payload["earliestStart"] == "09:30"
    assert payload["allowedGapMinutes"] == 90
    assert payload["fixedSections"] == {"CSE 123": ["A", "AA"]}


@pytest.mark.parametrize("invalid_time", ["9:30", "09:30:00", "24:00", "09:60"])
def test_preferences_reject_invalid_earliest_start(invalid_time: str) -> None:
    with pytest.raises(ValidationError, match="24-hour HH:MM format"):
        Preferences.model_validate({"earliestStart": invalid_time})


@pytest.mark.parametrize(
    "field_name", ["allowedGapMinutes", "minimumLongGapMinutes"]
)
def test_preferences_reject_negative_gap_values(field_name: str) -> None:
    with pytest.raises(ValidationError):
        Preferences.model_validate({field_name: -1})


def test_request_rejects_unknown_fixed_course(
    sample_request_data: dict[str, object],
) -> None:
    invalid_request = deepcopy(sample_request_data)
    invalid_request["preferences"]["fixedSections"] = {"CSE 999": ["A"]}

    with pytest.raises(ValidationError, match="fixed section course does not exist"):
        GenerateScheduleRequest.model_validate(invalid_request)


def test_request_rejects_unknown_fixed_section(
    sample_request_data: dict[str, object],
) -> None:
    invalid_request = deepcopy(sample_request_data)
    invalid_request["preferences"]["fixedSections"] = {"CSE 414": ["missing"]}

    with pytest.raises(ValidationError, match="fixed section does not exist"):
        GenerateScheduleRequest.model_validate(invalid_request)


def test_sample_data_matches_request_model(sample_request_data: dict[str, object]) -> None:
    request = GenerateScheduleRequest.model_validate(sample_request_data)

    assert len(request.courses) == 2
    assert request.preferences.earliest_start is not None
    assert request.max_results == 10
    assert request.model_dump(mode="json", by_alias=True)["maxResults"] == 10


def test_request_schema_uses_documented_json_names() -> None:
    properties = GenerateScheduleRequest.model_json_schema(by_alias=True)["properties"]

    assert set(properties) == {"courses", "preferences", "maxResults"}


def test_core_model_schemas_use_documented_fields() -> None:
    meeting_schema = Meeting.model_json_schema(by_alias=True)
    section_schema = Section.model_json_schema(by_alias=True)
    group_schema = SectionGroup.model_json_schema(by_alias=True)
    course_schema = Course.model_json_schema(by_alias=True)
    preferences_schema = Preferences.model_json_schema(by_alias=True)

    assert set(meeting_schema["properties"]) == {
        "days",
        "startTime",
        "endTime",
        "location",
    }
    assert set(meeting_schema["required"]) == {"days", "startTime", "endTime"}
    assert set(section_schema["required"]) == {
        "id",
        "type",
        "status",
        "meetings",
    }
    assert set(group_schema["properties"]) == {"type", "choose", "sections"}
    assert set(course_schema["properties"]) == {
        "courseCode",
        "title",
        "sectionGroups",
    }
    assert set(preferences_schema["properties"]) == {
        "earliestStart",
        "allowEarlierIfOnlyOption",
        "allowedGapMinutes",
        "minimumLongGapMinutes",
        "requireOpenSections",
        "fixedSections",
    }


def test_unknown_section_dependency_is_rejected(
    sample_request_data: dict[str, object],
) -> None:
    invalid_request = deepcopy(sample_request_data)
    courses = invalid_request["courses"]
    courses[0]["sectionGroups"][1]["sections"][0]["requiredSectionIds"] = [
        "missing"
    ]

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
                            "groupType": "lecture",
                            "section": {
                                "id": "C",
                                "type": "lecture",
                                "status": "open",
                                "meetings": [
                                    {
                                        "days": ["M", "W", "F"],
                                        "startTime": "12:30",
                                        "endTime": "13:20",
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
