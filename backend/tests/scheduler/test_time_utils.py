import pytest

from app.models import Meeting
from app.scheduler.time_utils import meetings_overlap


def meeting(days: list[str], start: str, end: str) -> Meeting:
    return Meeting.model_validate(
        {"days": days, "startTime": start, "endTime": end}
    )


@pytest.mark.parametrize(
    ("left_times", "right_times"),
    [
        (("09:30", "10:20"), ("09:30", "10:20")),
        (("09:30", "10:20"), ("10:00", "10:50")),
        (("09:30", "11:20"), ("10:00", "10:50")),
    ],
)
def test_meetings_detect_all_overlap_shapes(
    left_times: tuple[str, str],
    right_times: tuple[str, str],
) -> None:
    left = meeting(["M", "W"], *left_times)
    right = meeting(["W"], *right_times)

    assert meetings_overlap(left, right)


def test_adjacent_meetings_do_not_overlap() -> None:
    left = meeting(["M"], "09:30", "10:20")
    right = meeting(["M"], "10:20", "11:10")

    assert not meetings_overlap(left, right)


def test_same_time_on_different_days_does_not_overlap() -> None:
    left = meeting(["M"], "09:30", "10:20")
    right = meeting(["T"], "09:30", "10:20")

    assert not meetings_overlap(left, right)
