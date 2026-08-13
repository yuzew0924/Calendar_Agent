from __future__ import annotations

from ..models import ParsedPreferences
from .solver import ScheduleCandidate


def explain_schedule(
    candidate: ScheduleCandidate,
    preferences: ParsedPreferences,
) -> tuple[str, ...]:
    """Return baseline explanations until preference explanations are implemented."""
    del candidate, preferences
    return ("No time conflicts",)
