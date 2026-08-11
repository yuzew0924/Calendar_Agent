import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models import GenerateScheduleRequest, Meeting, SectionGroup


SAMPLE_DATA_PATH = Path(__file__).resolve().parents[2] / "sample-data" / "courses.json"


@pytest.fixture
def valid_request_data() -> dict[str, object]:
    return json.loads(SAMPLE_DATA_PATH.read_text())


def test_valid_sample_input_passes(valid_request_data: dict[str, object]) -> None:
    request = GenerateScheduleRequest.model_validate(valid_request_data)
    statuses = {
        section.status.value
        for course in request.courses
        for group in course.section_groups
        for section in group.sections
    }

    assert len(request.courses) == 2
    assert {"open", "closed"}.issubset(statuses)


def test_invalid_weekday_fails() -> None:
    with pytest.raises(ValidationError):
        Meeting.model_validate(
            {
                "days": ["Saturday"],
                "startTime": "09:30",
                "endTime": "10:20",
            }
        )


def test_invalid_time_format_fails() -> None:
    with pytest.raises(ValidationError, match="24-hour HH:MM format"):
        Meeting.model_validate(
            {
                "days": ["M"],
                "startTime": "9:30",
                "endTime": "10:20",
            }
        )


def test_start_time_after_end_time_fails() -> None:
    with pytest.raises(ValidationError, match="startTime must be earlier than endTime"):
        Meeting.model_validate(
            {
                "days": ["M"],
                "startTime": "11:20",
                "endTime": "10:20",
            }
        )


def test_unknown_fixed_section_fails(valid_request_data: dict[str, object]) -> None:
    invalid_request = deepcopy(valid_request_data)
    invalid_request["preferences"]["fixedSections"] = {"CSE 414": ["missing"]}

    with pytest.raises(ValidationError, match="fixed section does not exist"):
        GenerateScheduleRequest.model_validate(invalid_request)


def test_invalid_section_group_choose_fails() -> None:
    with pytest.raises(ValidationError, match="choose cannot exceed"):
        SectionGroup.model_validate(
            {
                "type": "quiz",
                "choose": 2,
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
