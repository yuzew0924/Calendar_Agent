from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import time
from enum import IntEnum, StrEnum
from typing import Protocol


TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class DayCode(StrEnum):
    MONDAY = "M"
    TUESDAY = "T"
    WEDNESDAY = "W"
    THURSDAY = "Th"
    FRIDAY = "F"


class Weekday(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4


WEEKDAY_BY_CODE: dict[DayCode, Weekday] = {
    DayCode.MONDAY: Weekday.MONDAY,
    DayCode.TUESDAY: Weekday.TUESDAY,
    DayCode.WEDNESDAY: Weekday.WEDNESDAY,
    DayCode.THURSDAY: Weekday.THURSDAY,
    DayCode.FRIDAY: Weekday.FRIDAY,
}


class MeetingLike(Protocol):
    days: list[DayCode]
    start_time: time
    end_time: time


@dataclass(frozen=True, slots=True)
class NormalizedMeeting:
    weekday: Weekday
    start_minute: int
    end_minute: int


def normalize_day_code(value: DayCode | str) -> Weekday:
    """Convert a public weekday code to its stable algorithmic value."""
    try:
        day_code = value if isinstance(value, DayCode) else DayCode(value)
    except ValueError as error:
        raise ValueError("weekday must be one of: M, T, W, Th, F") from error
    return WEEKDAY_BY_CODE[day_code]


def parse_time_string(value: str) -> time:
    """Parse a strict 24-hour HH:MM value."""
    if TIME_PATTERN.fullmatch(value) is None:
        raise ValueError("time must use 24-hour HH:MM format")

    hour, minute = (int(part) for part in value.split(":"))
    return time(hour=hour, minute=minute)


def time_to_minutes(value: str | time) -> int:
    """Convert a time value to minutes since midnight for numeric comparison."""
    parsed = parse_time_string(value) if isinstance(value, str) else value
    return parsed.hour * 60 + parsed.minute


def normalize_meeting(meeting: MeetingLike) -> tuple[NormalizedMeeting, ...]:
    """Expand a recurring meeting into one normalized interval per weekday."""
    start_minute = time_to_minutes(meeting.start_time)
    end_minute = time_to_minutes(meeting.end_time)

    return tuple(
        NormalizedMeeting(
            weekday=normalize_day_code(day),
            start_minute=start_minute,
            end_minute=end_minute,
        )
        for day in meeting.days
    )
