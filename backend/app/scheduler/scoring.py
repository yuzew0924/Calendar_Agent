from __future__ import annotations

from ..models import ParsedPreferences
from .solver import ScheduleCandidate


def score_schedule(
    candidate: ScheduleCandidate,
    preferences: ParsedPreferences,
) -> float:
    """Return the baseline score until preference scoring is implemented."""
    del candidate, preferences
    return 100.0
