import pytest

from app.models import Course, ParsedPreferences, ScheduleRequest, SectionGroup
from app.scheduler.explanations import explain_schedule
from app.scheduler.scoring import score_schedule
from app.scheduler.solver import (
    generate_course_combinations,
    generate_group_combinations,
    generate_schedule_candidates,
)


def section(
    section_id: str,
    *,
    day: str = "M",
    start: str = "09:30",
    end: str = "10:20",
    status: str = "open",
    required_section_ids: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": section_id,
        "status": status,
        "meetings": [{"days": [day], "startTime": start, "endTime": end}],
        "requiredSectionIds": required_section_ids or [],
    }


def section_without_meetings(section_id: str) -> dict[str, object]:
    return {"id": section_id, "status": "open", "meetings": []}


def test_group_combinations_select_one_section() -> None:
    group = SectionGroup.model_validate(
        {
            "type": "lab",
            "sections": [
                section_without_meetings("AA"),
                section_without_meetings("AB"),
                section_without_meetings("AC"),
            ],
        }
    )

    choices = generate_group_combinations(group)

    assert len(choices) == 3
    assert all(len(choice) == 1 for choice in choices)


@pytest.mark.parametrize(
    ("groups", "expected_count"),
    [
        ([("lecture", ["A", "B"])], 2),
        ([("lecture", ["A", "B"]), ("lab", ["AL", "BL", "CL"])], 6),
        ([("lecture", ["A", "B"]), ("quiz", ["AA", "AB"])], 4),
        (
            [
                ("lecture", ["A", "B"]),
                ("quiz", ["AA", "AB"]),
                ("lab", ["AL", "BL"]),
            ],
            8,
        ),
    ],
)
def test_course_combinations_follow_only_declared_groups(
    groups: list[tuple[str, list[str]]], expected_count: int
) -> None:
    course = Course.model_validate(
        {
            "code": "TEST 101",
            "groups": [
                {
                    "type": group_type,
                    "sections": [
                        section_without_meetings(section_id)
                        for section_id in section_ids
                    ],
                }
                for group_type, section_ids in groups
            ],
        }
    )

    choices = generate_course_combinations(course)

    assert len(choices) == expected_count
    assert all(len(choice) == len(groups) for choice in choices)
    assert all(
        len({selected.group_type for selected in choice}) == len(groups)
        for choice in choices
    )


def test_empty_declared_group_produces_no_course_combinations() -> None:
    course = Course.model_validate(
        {
            "code": "CHEM 142",
            "groups": [
                {
                    "type": "lecture",
                    "sections": [section_without_meetings("A")],
                },
                {"type": "lab", "sections": []},
            ],
        }
    )

    assert generate_course_combinations(course) == ()


def test_course_with_empty_group_produces_no_final_schedules() -> None:
    request = ScheduleRequest.model_validate(
        {
            "courses": [
                {
                    "code": "CSE 373",
                    "groups": [
                        {
                            "type": "lecture",
                            "sections": [section_without_meetings("A")],
                        }
                    ],
                },
                {
                    "code": "CHEM 142",
                    "groups": [
                        {
                            "type": "lecture",
                            "sections": [section_without_meetings("A")],
                        },
                        {"type": "lab", "sections": []},
                    ],
                },
            ]
        }
    )

    assert generate_schedule_candidates(request) == ()


def test_course_combinations_filter_closed_and_keep_fixed_sections() -> None:
    course = Course.model_validate(
        {
            "code": "CSE 373",
            "groups": [
                {
                    "type": "lecture",
                    "choose": 1,
                    "sections": [
                        section("A"),
                        section("B", start="11:30", end="12:20"),
                        section(
                            "C",
                            start="12:30",
                            end="13:20",
                            status="closed",
                        ),
                    ],
                }
            ],
        }
    )

    choices = generate_course_combinations(course, fixed_section_ids={"B"})

    assert len(choices) == 1
    assert choices[0][0].section.id == "B"


def test_course_combinations_enforce_section_dependencies() -> None:
    course = Course.model_validate(
        {
            "code": "CHEM 142",
            "groups": [
                {
                    "type": "lecture",
                    "choose": 1,
                    "sections": [
                        section("A"),
                        section("B", start="11:30", end="12:20"),
                    ],
                },
                {
                    "type": "lab",
                    "choose": 1,
                    "sections": [
                        section(
                            "AA",
                            day="T",
                            start="13:30",
                            end="15:20",
                            required_section_ids=["A"],
                        )
                    ],
                },
            ],
        }
    )

    choices = generate_course_combinations(course)

    assert len(choices) == 1
    assert {choice.section.id for choice in choices[0]} == {"A", "AA"}


def test_generate_schedules_filters_cross_course_conflicts() -> None:
    request = ScheduleRequest.model_validate(
        {
            "courses": [
                {
                    "code": "CSE 373",
                    "groups": [
                        {
                            "type": "lecture",
                            "choose": 1,
                            "sections": [section("A")],
                        }
                    ],
                },
                {
                    "code": "INFO 370",
                    "groups": [
                        {
                            "type": "lecture",
                            "choose": 1,
                            "sections": [
                                section("A", start="10:00", end="10:50"),
                                section("B", start="10:30", end="11:20"),
                            ],
                        }
                    ],
                },
            ],
            "preferences": {"requireOpenSections": True},
        }
    )

    schedules = generate_schedule_candidates(request)

    assert len(schedules) == 1
    assert {choice.section.id for choice in schedules[0]} == {"A", "B"}
    assert {choice.course_code for choice in schedules[0]} == {
        "CSE 373",
        "INFO 370",
    }


def test_scoring_and_explanation_extension_points_are_callable() -> None:
    preferences = ParsedPreferences()

    assert score_schedule((), preferences) == 100.0
    assert explain_schedule((), preferences) == ("No time conflicts",)
