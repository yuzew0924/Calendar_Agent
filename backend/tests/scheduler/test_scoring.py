from __future__ import annotations

from app.models import Preferences, Section
from app.scheduler.explanations import build_schedule_explanations
from app.scheduler.ranking import rank_schedules
from app.scheduler.scoring import calculate_daily_gaps, evaluate_schedule
from app.scheduler.solver import (
    CourseCombination,
    ScheduleCandidate,
    SectionChoice,
)
from app.models import SectionType


def candidate(*meetings: tuple[str, str, str, str]) -> ScheduleCandidate:
    courses = []
    for index, (section_id, day, start, end) in enumerate(meetings):
        section = Section.model_validate(
            {
                "id": section_id,
                "status": "open",
                "meetings": [
                    {"days": [day], "startTime": start, "endTime": end}
                ],
            }
        )
        courses.append(
            CourseCombination(
                course_code=f"CSE {100 + index}",
                selections=(SectionChoice(SectionType.LECTURE, section),),
            )
        )
    return ScheduleCandidate(courses=tuple(courses))


def score_for(schedule: ScheduleCandidate, rule: str) -> float:
    evaluation = evaluate_schedule(schedule, Preferences())
    return next(item.score for item in evaluation.breakdown if item.rule_name == rule)


def test_daily_gaps_are_grouped_sorted_and_ignore_different_days() -> None:
    schedule = candidate(
        ("A", "M", "11:30", "12:20"),
        ("B", "M", "09:30", "10:20"),
        ("C", "T", "09:30", "10:20"),
    )

    gaps = calculate_daily_gaps(schedule)

    assert [gap.minutes for gap in gaps[next(day for day in gaps if day.value == "M")]] == [70]
    assert gaps[next(day for day in gaps if day.value == "T")] == ()


def test_touching_classes_have_zero_gap() -> None:
    schedule = candidate(
        ("A", "M", "09:30", "10:20"),
        ("B", "M", "10:20", "11:10"),
    )

    monday = next(iter(calculate_daily_gaps(schedule).values()))

    assert monday[0].minutes == 0


def test_later_schedule_scores_higher_for_earliest_start_preference() -> None:
    early = candidate(("A", "M", "08:30", "09:20"))
    late = candidate(("B", "M", "11:30", "12:20"))
    preferences = Preferences(
        earliest_start="11:00",
        allow_earlier_if_only_option=True,
    )

    assert evaluate_schedule(late, preferences).score > evaluate_schedule(
        early, preferences
    ).score


def test_allow_earlier_fallback_reduces_early_class_penalty() -> None:
    schedule = candidate(("A", "M", "09:30", "10:20"))
    strict = Preferences(earliest_start="11:00", allow_earlier_if_only_option=False)
    flexible = Preferences(earliest_start="11:00", allow_earlier_if_only_option=True)

    assert evaluate_schedule(schedule, flexible).score > evaluate_schedule(
        schedule, strict
    ).score


def test_afternoon_preference_rewards_afternoon_meetings() -> None:
    morning = candidate(("A", "M", "09:30", "10:20"))
    afternoon = candidate(("B", "M", "13:30", "14:20"))
    preferences = Preferences(preferred_time_of_day="afternoon")

    assert evaluate_schedule(afternoon, preferences).score > evaluate_schedule(
        morning, preferences
    ).score


def test_fragmented_and_long_gaps_reduce_gap_score() -> None:
    compact = candidate(
        ("A", "M", "09:30", "10:20"),
        ("B", "M", "10:30", "11:20"),
    )
    fragmented = candidate(
        ("A", "M", "09:30", "10:20"),
        ("B", "M", "11:10", "12:00"),
    )
    long_gap = candidate(
        ("A", "M", "09:30", "10:20"),
        ("B", "M", "13:20", "14:10"),
    )

    assert score_for(compact, "gaps") > score_for(fragmented, "gaps")
    assert score_for(fragmented, "gaps") > score_for(long_gap, "gaps")


def test_preferred_day_off_is_soft_and_produces_tradeoff() -> None:
    friday_class = candidate(("A", "F", "11:30", "12:20"))
    monday_class = candidate(("B", "M", "11:30", "12:20"))
    preferences = Preferences(preferred_days_off=["F"])

    friday_evaluation = evaluate_schedule(friday_class, preferences)
    monday_evaluation = evaluate_schedule(monday_class, preferences)
    _, friday_tradeoffs = build_schedule_explanations(
        friday_class, preferences, friday_evaluation
    )

    assert monday_evaluation.score > friday_evaluation.score
    assert any("preferred day" in item for item in friday_tradeoffs)


def test_fixed_section_is_in_deterministic_reasons() -> None:
    schedule = candidate(("A", "M", "11:30", "12:20"))
    preferences = Preferences(fixed_sections={"CSE 100": ["A"]})

    reasons, _ = build_schedule_explanations(schedule, preferences)

    assert "Includes required section CSE 100 A" in reasons


def test_ranking_is_stable_limited_and_uses_section_signature_tie_breaker() -> None:
    schedule_b = candidate(("B", "M", "11:30", "12:20"))
    schedule_a = candidate(("A", "M", "11:30", "12:20"))
    candidates = (schedule_b, schedule_a)

    first = rank_schedules(candidates, Preferences(), top_n=1)
    second = rank_schedules(candidates, Preferences(), top_n=1)

    assert first == second
    assert len(first) == 1
    assert first[0].rank == 1
    assert first[0].candidate.courses[0].selections[0].section.id == "A"
