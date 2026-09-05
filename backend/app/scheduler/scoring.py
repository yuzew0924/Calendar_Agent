from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import time

from ..models import GapPreference, Preferences, PreferredTimeOfDay
from .solver import ScheduleCandidate
from .time_utils import DayCode, time_to_minutes


@dataclass(frozen=True, slots=True)
class MeetingFact:
    day: DayCode
    start: time
    end: time
    course_code: str
    section_id: str

    @property
    def label(self) -> str:
        return f"{self.course_code} {self.section_id}"


@dataclass(frozen=True, slots=True)
class GapDetail:
    day: DayCode
    start: time
    end: time
    minutes: int
    before: MeetingFact
    after: MeetingFact


@dataclass(frozen=True, slots=True)
class ScoringRuleResult:
    rule_name: str
    score: float
    maximum: float
    details: str
    reason: str | None = None
    tradeoff: str | None = None
    affected_sections: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ScoreEvaluation:
    score: float
    breakdown: tuple[ScoringRuleResult, ...]
    total_gap_minutes: int
    earliest_meeting_minute: int


def collect_meeting_facts(candidate: ScheduleCandidate) -> tuple[MeetingFact, ...]:
    facts = [
        MeetingFact(
            day=day,
            start=meeting.start_time,
            end=meeting.end_time,
            course_code=course.course_code,
            section_id=selection.section.id,
        )
        for course in candidate.courses
        for selection in course.selections
        for meeting in selection.section.meetings
        for day in meeting.days
    ]
    return tuple(
        sorted(
            facts,
            key=lambda fact: (
                fact.day.value,
                fact.start,
                fact.end,
                fact.course_code,
                fact.section_id,
            ),
        )
    )


def calculate_daily_gaps(
    candidate: ScheduleCandidate,
) -> dict[DayCode, tuple[GapDetail, ...]]:
    meetings_by_day: dict[DayCode, list[MeetingFact]] = defaultdict(list)
    for fact in collect_meeting_facts(candidate):
        meetings_by_day[fact.day].append(fact)

    gaps: dict[DayCode, tuple[GapDetail, ...]] = {}
    for day, meetings in meetings_by_day.items():
        ordered = sorted(meetings, key=lambda fact: (fact.start, fact.end, fact.label))
        gaps[day] = tuple(
            GapDetail(
                day=day,
                start=before.end,
                end=after.start,
                minutes=time_to_minutes(after.start) - time_to_minutes(before.end),
                before=before,
                after=after,
            )
            for before, after in zip(ordered, ordered[1:])
        )
    return gaps


def _score_earliest_start(
    facts: tuple[MeetingFact, ...], preferences: Preferences
) -> ScoringRuleResult:
    maximum = 25.0
    if preferences.earliest_start is None:
        return ScoringRuleResult(
            "earliestStart", maximum, maximum, "No earliest-start preference set"
        )

    earliest_by_day: dict[DayCode, MeetingFact] = {}
    for fact in facts:
        current = earliest_by_day.get(fact.day)
        if current is None or fact.start < current.start:
            earliest_by_day[fact.day] = fact

    preferred_minute = time_to_minutes(preferences.earliest_start)
    early = [
        fact
        for fact in earliest_by_day.values()
        if time_to_minutes(fact.start) < preferred_minute
    ]
    if not early:
        details = f"All class days start at or after {preferences.earliest_start:%H:%M}"
        return ScoringRuleResult(
            "earliestStart", maximum, maximum, details, reason=details
        )

    total_minutes_early = sum(
        preferred_minute - time_to_minutes(fact.start) for fact in early
    )
    penalty = min(maximum, total_minutes_early / 30 * 3)
    if preferences.allow_earlier_if_only_option:
        penalty *= 0.5
    labels = tuple(dict.fromkeys(fact.label for fact in early))
    return ScoringRuleResult(
        "earliestStart",
        round(maximum - penalty, 2),
        maximum,
        f"{len(early)} class day(s) start before {preferences.earliest_start:%H:%M}",
        tradeoff=f"{len(early)} class day(s) start before the preferred {preferences.earliest_start:%H:%M}",
        affected_sections=labels,
    )


def _time_bucket(value: time) -> PreferredTimeOfDay:
    if value.hour < 12:
        return PreferredTimeOfDay.MORNING
    if value.hour < 17:
        return PreferredTimeOfDay.AFTERNOON
    return PreferredTimeOfDay.EVENING


def _score_time_of_day(
    facts: tuple[MeetingFact, ...], preferences: Preferences
) -> ScoringRuleResult:
    maximum = 20.0
    preferred = preferences.preferred_time_of_day
    if preferred is PreferredTimeOfDay.NONE or not facts:
        return ScoringRuleResult(
            "preferredTimeOfDay", maximum, maximum, "No time-of-day preference set"
        )

    matching = [fact for fact in facts if _time_bucket(fact.start) is preferred]
    score = maximum * len(matching) / len(facts)
    details = (
        f"{len(matching)} of {len(facts)} weekly meetings start in the "
        f"{preferred.value}"
    )
    if len(matching) == len(facts):
        return ScoringRuleResult(
            "preferredTimeOfDay", maximum, maximum, details, reason=details
        )
    return ScoringRuleResult(
        "preferredTimeOfDay",
        round(score, 2),
        maximum,
        details,
        tradeoff=(
            f"{len(facts) - len(matching)} weekly meeting(s) fall outside the "
            f"preferred {preferred.value}"
        ),
        affected_sections=tuple(
            dict.fromkeys(fact.label for fact in facts if fact not in matching)
        ),
    )


def _score_gaps(
    candidate: ScheduleCandidate, preferences: Preferences
) -> ScoringRuleResult:
    maximum = 30.0
    gaps = tuple(
        gap for daily in calculate_daily_gaps(candidate).values() for gap in daily
    )
    total_gap = sum(max(0, gap.minutes) for gap in gaps)
    mode = preferences.gap_preference
    details = f"{total_gap} total idle minute(s) across {len(gaps)} adjacent class gap(s)"
    if mode is GapPreference.NONE:
        return ScoringRuleResult(
            "gaps", maximum, maximum, f"Gap preference not set; {details}"
        )

    if mode is GapPreference.COMPACT:
        penalties = [
            0 if gap.minutes <= 10 else 2 if gap.minutes < 30 else 7 if gap.minutes <= 90 else 12
            for gap in gaps
        ]
        reason = "Classes are consecutive or nearly consecutive" if gaps and all(gap.minutes <= 10 for gap in gaps) else None
        tradeoff = f"{sum(gap.minutes >= 30 for gap in gaps)} gap(s) are at least 30 minutes" if any(gap.minutes >= 30 for gap in gaps) else None
    elif mode is GapPreference.BREAKS:
        penalties = [
            8 if gap.minutes <= 10 else 2 if gap.minutes < 30 else 0 if gap.minutes <= 90 else 4 if gap.minutes <= 150 else 8
            for gap in gaps
        ]
        reason = "Provides useful breaks between classes" if gaps and any(30 <= gap.minutes <= 90 for gap in gaps) else None
        tradeoff = "Some classes are consecutive with little recovery time" if any(gap.minutes <= 10 for gap in gaps) else None
    else:
        penalties = [
            5 if gap.minutes <= 10 else 0 if gap.minutes <= 60 else 4 if gap.minutes <= 90 else 9
            for gap in gaps
        ]
        reason = "Provides moderate breaks without excessive fragmentation" if gaps and all(11 <= gap.minutes <= 60 for gap in gaps) else None
        tradeoff = "The day is either tightly packed or widely fragmented" if any(gap.minutes <= 10 or gap.minutes > 90 for gap in gaps) else None

    score = max(0.0, maximum - sum(penalties))
    affected = tuple(dict.fromkeys(label for gap in gaps for label in (gap.before.label, gap.after.label)))
    return ScoringRuleResult(
        "gaps",
        round(score, 2),
        maximum,
        f"{mode.value} preference: {details}",
        reason=reason,
        tradeoff=tradeoff,
        affected_sections=affected,
    )


def _score_preferred_days_off(
    facts: tuple[MeetingFact, ...], preferences: Preferences
) -> ScoringRuleResult:
    maximum = 25.0
    preferred = preferences.preferred_days_off
    if not preferred:
        return ScoringRuleResult(
            "preferredDaysOff", maximum, maximum, "No preferred days off set"
        )
    active_days = {fact.day for fact in facts}
    satisfied = [day for day in preferred if day not in active_days]
    missed = [day for day in preferred if day in active_days]
    score = maximum * len(satisfied) / len(preferred)
    reason = (
        f"Keeps preferred day(s) off: {', '.join(day.value for day in satisfied)}"
        if satisfied
        else None
    )
    tradeoff = (
        f"Classes remain on preferred day(s) off: {', '.join(day.value for day in missed)}"
        if missed
        else None
    )
    return ScoringRuleResult(
        "preferredDaysOff",
        round(score, 2),
        maximum,
        f"{len(satisfied)} of {len(preferred)} preferred day(s) are free",
        reason=reason,
        tradeoff=tradeoff,
        affected_sections=tuple(
            dict.fromkeys(fact.label for fact in facts if fact.day in missed)
        ),
    )


def evaluate_schedule(
    candidate: ScheduleCandidate,
    preferences: Preferences,
) -> ScoreEvaluation:
    facts = collect_meeting_facts(candidate)
    breakdown = (
        _score_earliest_start(facts, preferences),
        _score_time_of_day(facts, preferences),
        _score_gaps(candidate, preferences),
        _score_preferred_days_off(facts, preferences),
    )
    gaps = calculate_daily_gaps(candidate)
    total_gap = sum(
        max(0, gap.minutes) for daily_gaps in gaps.values() for gap in daily_gaps
    )
    earliest = min((time_to_minutes(fact.start) for fact in facts), default=24 * 60)
    return ScoreEvaluation(
        score=round(sum(item.score for item in breakdown), 2),
        breakdown=breakdown,
        total_gap_minutes=total_gap,
        earliest_meeting_minute=earliest,
    )


def score_schedule(candidate: ScheduleCandidate, preferences: Preferences) -> float:
    return evaluate_schedule(candidate, preferences).score
