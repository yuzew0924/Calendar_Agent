from __future__ import annotations

from ..models import Preferences
from .solver import ScheduleCandidate


def score_schedule(
    candidate: ScheduleCandidate,
    preferences: Preferences,
) -> float:
    """Return the baseline score until preference scoring is implemented."""
    del candidate, preferences
    return 100.0
