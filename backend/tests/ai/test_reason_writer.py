import asyncio
import json
from typing import Any

from app.ai.client import AIConnectionFailure
from app.ai.reason_writer import ReasonWriter
from app.models import Preferences, Section, SectionType
from app.scheduler.solver import CourseCombination, ScheduleCandidate, SectionChoice


class FakeClient:
    def __init__(self, output: str | Exception) -> None:
        self.output = output

    async def generate_text(self, **request: Any) -> str:
        del request
        if isinstance(self.output, Exception):
            raise self.output
        return self.output


def schedule() -> ScheduleCandidate:
    section = Section.model_validate(
        {
            "id": "A",
            "status": "open",
            "meetings": [
                {
                    "days": ["M"],
                    "startTime": "10:30",
                    "endTime": "11:20",
                }
            ],
        }
    )
    return ScheduleCandidate(
        courses=(
            CourseCombination(
                course_code="CSE 373",
                selections=(SectionChoice(SectionType.LECTURE, section),),
            ),
        )
    )


def rewrite(output: str | Exception) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return asyncio.run(
        ReasonWriter(FakeClient(output)).rewrite_or_fallback(
            schedule(),
            Preferences(),
            ("Includes CSE 373 A",),
            ("Starts at 10:30",),
        )
    )


def test_reason_writer_accepts_grounded_rewrite() -> None:
    output = json.dumps(
        {
            "reasons": ["Includes CSE 373 section A"],
            "tradeoffs": ["The class starts at 10:30"],
        }
    )

    assert rewrite(output) == (
        ("Includes CSE 373 section A",),
        ("The class starts at 10:30",),
    )


def test_reason_writer_falls_back_on_hallucinated_fact() -> None:
    output = json.dumps(
        {
            "reasons": ["Includes CSE 999 at 08:30"],
            "tradeoffs": ["No issue"],
        }
    )

    assert rewrite(output) == (("Includes CSE 373 A",), ("Starts at 10:30",))

    wrong_section = json.dumps(
        {
            "reasons": ["Includes CSE 373 Z"],
            "tradeoffs": ["Starts at 10:30"],
        }
    )
    assert rewrite(wrong_section) == (
        ("Includes CSE 373 A",),
        ("Starts at 10:30",),
    )

    invented_location = json.dumps(
        {
            "reasons": ["Includes CSE 373 section A in KNE 120"],
            "tradeoffs": ["Starts at 10:30"],
        }
    )
    assert rewrite(invented_location) == (
        ("Includes CSE 373 A",),
        ("Starts at 10:30",),
    )

    unknown_day = json.dumps(
        {"reasons": ["Includes section Z"], "tradeoffs": ["Meets on Sunday"]}
    )
    assert rewrite(unknown_day) == (
        ("Includes CSE 373 A",),
        ("Starts at 10:30",),
    )


def test_reason_writer_falls_back_on_ai_or_schema_failure() -> None:
    assert rewrite(AIConnectionFailure("offline")) == (
        ("Includes CSE 373 A",),
        ("Starts at 10:30",),
    )
    assert rewrite("not json") == (
        ("Includes CSE 373 A",),
        ("Starts at 10:30",),
    )
