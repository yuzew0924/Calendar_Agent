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
    group_type: SectionType
    section: Section


@dataclass(frozen=True, slots=True)
class CourseCombination:
    course_code: str
    selections: tuple[SectionChoice, ...]


@dataclass(frozen=True, slots=True)
class ScheduleCandidate:
    courses: tuple[CourseCombination, ...]


def generate_group_combinations(group: SectionGroup) -> tuple[tuple[Section, ...], ...]:
    """Return one candidate for each individual section in a required group."""
    return tuple((section,) for section in group.sections)


def _dependencies_are_satisfied(selections: tuple[SectionChoice, ...]) -> bool:
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
) -> tuple[CourseCombination, ...]:
    """Generate valid combinations containing one section from every group."""
    fixed_ids = fixed_section_ids or set()
    group_combinations = [generate_group_combinations(group) for group in course.groups]
    candidates: list[CourseCombination] = []

    for group_selection in product(*group_combinations):
        choices = tuple(
            SectionChoice(group.type, section)
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
        candidate = CourseCombination(course_code=course.code, selections=choices)
        if course_combination_has_conflict(candidate):
            continue

        candidates.append(candidate)

    return tuple(candidates)


def sections_overlap(left: Section, right: Section) -> bool:
    return any(
        meetings_overlap(left_meeting, right_meeting)
        for left_meeting in left.meetings
        for right_meeting in right.meetings
    )


def course_combination_has_conflict(candidate: CourseCombination) -> bool:
    return any(
        sections_overlap(left.section, right.section)
        for left, right in combinations(candidate.selections, 2)
    )


def schedule_has_conflict(candidate: ScheduleCandidate) -> bool:
    selections = tuple(
        selection
        for course_combination in candidate.courses
        for selection in course_combination.selections
    )
    return any(
        sections_overlap(left.section, right.section)
        for left, right in combinations(selections, 2)
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
        candidate = ScheduleCandidate(courses=tuple(course_selection))
        if not schedule_has_conflict(candidate):
            schedules.append(candidate)

    return tuple(schedules)
