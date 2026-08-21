import pytest

from app.ai.context import build_ai_course_context
from app.models import Course


def test_course_context_contains_only_allowlisted_ai_fields() -> None:
    course = Course.model_validate(
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
                            "sln": "12345",
                            "requiredSectionIds": [],
                            "meetings": [
                                {
                                    "days": ["M", "W", "F"],
                                    "startTime": "09:30",
                                    "endTime": "10:20",
                                    "location": "KNE 120",
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    )

    payload = build_ai_course_context([course]).model_dump(
        mode="json",
        by_alias=True,
    )

    assert payload == {
        "courses": [
            {
                "courseCode": "CSE 373",
                "title": "Data Structures and Algorithms",
                "sections": [
                    {
                        "id": "A",
                        "type": "lecture",
                        "status": "open",
                        "meetings": [
                            {
                                "days": ["M", "W", "F"],
                                "startTime": "09:30",
                                "endTime": "10:20",
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_course_context_requires_at_least_one_course() -> None:
    with pytest.raises(
        ValueError,
        match="at least one course is required for AI preference parsing",
    ):
        build_ai_course_context([])
