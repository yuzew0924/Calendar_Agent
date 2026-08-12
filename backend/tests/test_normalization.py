from datetime import time

import pytest

from app.models import Meeting
from app.normalization import (
    Weekday,
    normalize_day_code,
    normalize_meeting,
    parse_time_string,
    time_to_minutes,
)


@pytest.mark.parametrize(
    ("code", "weekday"),
    [
        ("M", Weekday.MONDAY),
        ("T", Weekday.TUESDAY),
        ("W", Weekday.WEDNESDAY),
        ("Th", Weekday.THURSDAY),
        ("F", Weekday.FRIDAY),
    ],
)
def test_normalize_day_code(code: str, weekday: Weekday) -> None:
    assert normalize_day_code(code) is weekday


def test_weekday_values_have_stable_order() -> None:
    assert list(Weekday) == [
        Weekday.MONDAY,
        Weekday.TUESDAY,
        Weekday.WEDNESDAY,
        Weekday.THURSDAY,
        Weekday.FRIDAY,
    ]


def test_invalid_day_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="weekday must be one of"):
        normalize_day_code("Saturday")


@pytest.mark.parametrize(
    ("value", "minutes"),
    [("00:00", 0), ("09:30", 570), ("13:20", 800), ("23:59", 1439)],
)
def test_time_string_converts_to_minutes(value: str, minutes: int) -> None:
    assert time_to_minutes(value) == minutes


def test_time_object_converts_with_the_same_logic() -> None:
    assert time_to_minutes(time(hour=9, minute=30)) == 570


@pytest.mark.parametrize("value", ["9:30", "09:30:00", "24:00", "09:60"])
def test_invalid_time_string_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="24-hour HH:MM format"):
        parse_time_string(value)


def test_meeting_expands_to_numeric_weekday_intervals() -> None:
    meeting = Meeting.model_validate(
        {
            "days": ["M", "W", "F"],
            "startTime": "09:30",
            "endTime": "10:20",
            "location": "KNE 120",
        }
    )

    intervals = normalize_meeting(meeting)

    assert [interval.weekday for interval in intervals] == [
        Weekday.MONDAY,
        Weekday.WEDNESDAY,
        Weekday.FRIDAY,
    ]
    assert all(interval.start_minute == 570 for interval in intervals)
    assert all(interval.end_minute == 620 for interval in intervals)
