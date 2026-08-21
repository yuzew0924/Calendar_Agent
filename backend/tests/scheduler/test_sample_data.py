import json
from pathlib import Path

from app.models import GenerateScheduleRequest
from app.scheduler.solver import (
    generate_schedule_candidates,
    schedule_has_conflict,
    schedule_satisfies_hard_constraints,
)


SAMPLE_DATA_PATH = (
    Path(__file__).resolve().parents[3] / "sample-data" / "courses.json"
)


def test_sample_data_generates_stable_conflict_free_schedules() -> None:
    payload = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    request = GenerateScheduleRequest.model_validate(payload)

    first_run = generate_schedule_candidates(request)
    second_run = generate_schedule_candidates(request)

    assert len(first_run) == 2
    assert first_run == second_run
    assert all(not schedule_has_conflict(candidate) for candidate in first_run)
    assert all(
        schedule_satisfies_hard_constraints(candidate, request)
        for candidate in first_run
    )
