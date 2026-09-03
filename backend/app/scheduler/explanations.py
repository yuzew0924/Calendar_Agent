from __future__ import annotations

from ..models import Preferences
from .scoring import ScoreEvaluation, evaluate_schedule
from .solver import ScheduleCandidate


def build_schedule_explanations(
    candidate: ScheduleCandidate,
    preferences: Preferences,
    evaluation: ScoreEvaluation | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    result = evaluation or evaluate_schedule(candidate, preferences)
    reasons = ["No time conflicts"]
    tradeoffs: list[str] = []

    for course_code, section_ids in preferences.fixed_sections.items():
        for section_id in section_ids:
            reasons.append(f"Includes required section {course_code} {section_id}")

    if candidate.courses:
        reasons.extend(item.reason for item in result.breakdown if item.reason)
    tradeoffs.extend(item.tradeoff for item in result.breakdown if item.tradeoff)
    return tuple(dict.fromkeys(reasons)), tuple(dict.fromkeys(tradeoffs))


def explain_schedule(
    candidate: ScheduleCandidate,
    preferences: Preferences,
) -> tuple[str, ...]:
    reasons, _ = build_schedule_explanations(candidate, preferences)
    return reasons
