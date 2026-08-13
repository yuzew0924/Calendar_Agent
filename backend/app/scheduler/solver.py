from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product

from ..models import (
    Course,
    ScheduleRequest,
    Section,
    SectionGroup,
    SectionStatus,
    SectionType,
)
from .time_utils import meetings_overlap


@dataclass(frozen=True, slots=True)
class SectionChoice:
    course_code: str
    group_type: SectionType
    section: Section


ScheduleCandidate = tuple[SectionChoice, ...]


def generate_group_combinations(group: SectionGroup) -> tuple[tuple[Section, ...], ...]:
    """Return every exact-size section selection allowed by one group."""
    return tuple(combinations(group.sections, group.choose))


def _dependencies_are_satisfied(selections: ScheduleCandidate) -> bool:
    selected_ids = {choice.section.id for choice in selections}
    return all(
        set(choice.section.required_section_ids).issubset(selected_ids)
        for choice in selections
    )


def generate_course_combinations(
    course: Course,
    *,
    require_open_sections: bool = True,
    fixed_section_ids: set[str] | None = None,
) -> tuple[ScheduleCandidate, ...]:
    """Generate valid exact-choice combinations for a single course."""
    fixed_ids = fixed_section_ids or set()
    group_combinations = [generate_group_combinations(group) for group in course.groups]
    candidates: list[ScheduleCandidate] = []

    for group_selection in product(*group_combinations):
        choices = tuple(
            SectionChoice(course.code, group.type, section)
            for group, selected_sections in zip(course.groups, group_selection, strict=True)
            for section in selected_sections
        )
        selected_ids = {choice.section.id for choice in choices}

        if not fixed_ids.issubset(selected_ids):
            continue
        if require_open_sections and any(
            choice.section.status is not SectionStatus.OPEN for choice in choices
        ):
            continue
        if not _dependencies_are_satisfied(choices):
            continue
        if schedule_has_conflict(choices):
            continue

        candidates.append(choices)

    return tuple(candidates)


def sections_overlap(left: Section, right: Section) -> bool:
    return any(
        meetings_overlap(left_meeting, right_meeting)
        for left_meeting in left.meetings
        for right_meeting in right.meetings
    )


def schedule_has_conflict(candidate: ScheduleCandidate) -> bool:
    return any(
        sections_overlap(left.section, right.section)
        for left, right in combinations(candidate, 2)
    )


def generate_schedule_candidates(request: ScheduleRequest) -> tuple[ScheduleCandidate, ...]:
    """Generate all conflict-free multi-course schedules for a validated request."""
    course_candidates = [
        generate_course_combinations(
            course,
            require_open_sections=request.preferences.require_open_sections,
            fixed_section_ids=set(request.preferences.fixed_sections.get(course.code, [])),
        )
        for course in request.courses
    ]

    schedules: list[ScheduleCandidate] = []
    for course_selection in product(*course_candidates):
        candidate = tuple(choice for choices in course_selection for choice in choices)
        if not schedule_has_conflict(candidate):
            schedules.append(candidate)

    return tuple(schedules)
