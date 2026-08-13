"""Compatibility exports for the scheduler time utilities."""

from .scheduler.time_utils import (
    TIME_PATTERN,
    DayCode,
    MeetingLike,
    NormalizedMeeting,
    Weekday,
    intervals_overlap,
    meetings_overlap,
    normalize_day_code,
    normalize_meeting,
    parse_time_string,
    time_to_minutes,
)

__all__ = [
    "TIME_PATTERN",
    "DayCode",
    "MeetingLike",
    "NormalizedMeeting",
    "Weekday",
    "intervals_overlap",
    "meetings_overlap",
    "normalize_day_code",
    "normalize_meeting",
    "parse_time_string",
    "time_to_minutes",
]
