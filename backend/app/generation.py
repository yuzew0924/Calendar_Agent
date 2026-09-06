from __future__ import annotations

from .ai.preference_parser import PreferenceParser, validate_and_convert_preferences
from .ai.reason_writer import ReasonWriter
from .models import (
    GenerateSchedulesApiRequest,
    GenerateSchedulesApiResponse,
    AffectedMeeting,
    RankedSchedule,
    ScheduleRequest,
    ScheduleSection,
    ScoreBreakdownItem,
)
from .scheduler.ranking import ScheduleRankingResult, rank_schedules
from .scheduler.solver import diagnose_no_schedules, generate_schedule_candidates


def _schedule_sections(result: ScheduleRankingResult) -> list[ScheduleSection]:
    return [
        ScheduleSection(
            course_code=course.course_code,
            group_type=selection.group_type,
            section_id=selection.section.id,
            status=selection.section.status,
            sln=selection.section.sln,
            meetings=selection.section.meetings,
        )
        for course in result.candidate.courses
        for selection in course.selections
    ]


async def generate_ranked_schedules(
    request: GenerateSchedulesApiRequest,
    *,
    parser: PreferenceParser | None = None,
    reason_writer: ReasonWriter | None = None,
) -> GenerateSchedulesApiResponse:
    if request.preferences is not None:
        parsed = request.preferences
    else:
        if parser is None or request.preferenceText is None:
            raise RuntimeError("a preference parser is required for preferenceText")
        parsed = await parser.parse(request.preferenceText, request.courses)

    preferences = validate_and_convert_preferences(parsed, request.courses)
    schedule_request = ScheduleRequest(
        courses=request.courses,
        preferences=preferences,
    )
    candidates = generate_schedule_candidates(schedule_request)
    ranked = rank_schedules(candidates, preferences, top_n=request.topN)

    schedules: list[RankedSchedule] = []
    for result in ranked:
        reasons = result.reasons
        tradeoffs = result.tradeoffs
        if request.enhanceReasons and reason_writer is not None:
            reasons, tradeoffs = await reason_writer.rewrite_or_fallback(
                result.candidate,
                preferences,
                reasons,
                tradeoffs,
            )
        schedules.append(
            RankedSchedule(
                rank=result.rank,
                score=result.score,
                sections=_schedule_sections(result),
                score_breakdown={
                    item.rule_name: ScoreBreakdownItem(
                        score=item.score,
                        maximum=item.maximum,
                        score_delta=item.score_delta,
                        matched_preference=item.matched_preference,
                        details=item.details,
                        reason_candidate=item.reason_candidate,
                        tradeoff_candidate=item.tradeoff_candidate,
                        affected_sections=list(item.affected_sections),
                        affected_meetings=[
                            AffectedMeeting(
                                course_code=fact.course_code,
                                section_id=fact.section_id,
                                day=fact.day,
                                start_time=fact.start,
                                end_time=fact.end,
                            )
                            for fact in item.affected_meetings
                        ],
                    )
                    for item in result.evaluation.breakdown
                },
                reasons=list(reasons),
                tradeoffs=list(tradeoffs),
            )
        )

    warnings = [] if schedules else list(diagnose_no_schedules(schedule_request))
    return GenerateSchedulesApiResponse(
        interpreted_preferences=parsed,
        schedules=schedules,
        count=len(schedules),
        warnings=warnings,
    )
