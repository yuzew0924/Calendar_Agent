from app.models import Meeting
from app.scheduler.time_utils import meetings_overlap


def meeting(days: list[str], start: str, end: str) -> Meeting:
    return Meeting.model_validate(
        {"days": days, "startTime": start, "endTime": end}
    )


def test_meetings_overlap_on_a_shared_day() -> None:
    left = meeting(["M", "W"], "09:30", "10:20")
    right = meeting(["W"], "10:00", "10:50")

    assert meetings_overlap(left, right)


def test_adjacent_meetings_do_not_overlap() -> None:
    left = meeting(["M"], "09:30", "10:20")
    right = meeting(["M"], "10:20", "11:10")

    assert not meetings_overlap(left, right)


def test_same_time_on_different_days_does_not_overlap() -> None:
    left = meeting(["M"], "09:30", "10:20")
    right = meeting(["T"], "09:30", "10:20")

    assert not meetings_overlap(left, right)
