from __future__ import annotations

from dataclasses import dataclass

from ..models import Preferences
from .explanations import build_schedule_explanations
from .scoring import ScoreEvaluation, evaluate_schedule
from .solver import ScheduleCandidate


@dataclass(frozen=True, slots=True)
class ScheduleRankingResult:
    rank: int
    candidate: ScheduleCandidate
    score: float
    evaluation: ScoreEvaluation
    reasons: tuple[str, ...]
    tradeoffs: tuple[str, ...]


def schedule_signature(
    candidate: ScheduleCandidate,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        (
            course.course_code,
            tuple(selection.section.id for selection in course.selections),
        )
        for course in candidate.courses
    )


def rank_schedules(
    candidates: tuple[ScheduleCandidate, ...],
    preferences: Preferences,
    *,
    top_n: int = 5,
) -> tuple[ScheduleRankingResult, ...]:
    evaluated = []
    for candidate in candidates:
        evaluation = evaluate_schedule(candidate, preferences)
        reasons, tradeoffs = build_schedule_explanations(
            candidate, preferences, evaluation
        )
        evaluated.append((candidate, evaluation, reasons, tradeoffs))

    evaluated.sort(
        key=lambda item: (
            -item[1].score,
            -item[1].earliest_meeting_minute,
            schedule_signature(item[0]),
        )
    )
    return tuple(
        ScheduleRankingResult(
            rank=index,
            candidate=candidate,
            score=evaluation.score,
            evaluation=evaluation,
            reasons=reasons,
            tradeoffs=tradeoffs,
        )
        for index, (candidate, evaluation, reasons, tradeoffs) in enumerate(
            evaluated[:top_n], start=1
        )
    )
