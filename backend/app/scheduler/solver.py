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


def generate_group_combinations(
    group: SectionGroup,
    *,
    require_open_sections: bool = False,
) -> tuple[tuple[Section, ...], ...]:
    """Return one eligible section choice for a required group."""
    return tuple(
        (section,)
        for section in group.sections
        if not require_open_sections or section.status is SectionStatus.OPEN
    )


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
    group_combinations = [
        generate_group_combinations(
            group,
            require_open_sections=require_open_sections,
        )
        for group in course.groups
    ]
    candidates: list[CourseCombination] = []

    for group_selection in product(*group_combinations):
        choices = tuple(
            SectionChoice(group.type, section)
            for group, selected_sections in zip(course.groups, group_selection, strict=True)
            for section in selected_sections
        )
        candidate = CourseCombination(course_code=course.code, selections=choices)
        if not course_combination_satisfies_hard_constraints(
            candidate,
            course,
            require_open_sections=require_open_sections,
            fixed_section_ids=fixed_ids,
        ):
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


def course_combination_satisfies_hard_constraints(
    candidate: CourseCombination,
    course: Course,
    *,
    require_open_sections: bool,
    fixed_section_ids: set[str],
) -> bool:
    """Validate one course selection against every course-level hard rule."""
    if candidate.course_code != course.code:
        return False
    if len(candidate.selections) != len(course.groups):
        return False

    for group, selection in zip(course.groups, candidate.selections, strict=True):
        sections_by_id = {section.id: section for section in group.sections}
        if selection.group_type is not group.type:
            return False
        if sections_by_id.get(selection.section.id) != selection.section:
            return False
        if (
            require_open_sections
            and selection.section.status is not SectionStatus.OPEN
        ):
            return False

    selected_ids = {choice.section.id for choice in candidate.selections}
    return (
        fixed_section_ids.issubset(selected_ids)
        and _dependencies_are_satisfied(candidate.selections)
        and not course_combination_has_conflict(candidate)
    )


def schedule_satisfies_hard_constraints(
    candidate: ScheduleCandidate,
    request: ScheduleRequest,
) -> bool:
    """Validate course coverage and every hard rule before returning a schedule."""
    if len(candidate.courses) != len(request.courses):
        return False

    if not all(
        course_combination_satisfies_hard_constraints(
            course_combination,
            course,
            require_open_sections=request.preferences.require_open_sections,
            fixed_section_ids=set(
                request.preferences.fixed_sections.get(course.code, [])
            ),
        )
        for course, course_combination in zip(
            request.courses,
            candidate.courses,
            strict=True,
        )
    ):
        return False

    return not schedule_has_conflict(candidate)


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
        if schedule_satisfies_hard_constraints(candidate, request):
            schedules.append(candidate)

    return tuple(schedules)
