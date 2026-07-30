from __future__ import annotations

import pytest

from posturely.core.analysis import IssueProgress
from posturely.core.state_machine import PostureStateMachine
from posturely.core.types import Evidence, PostureEvidence


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def evidence(*, head: bool, confident: bool = True) -> PostureEvidence:
    item = Evidence(
        problematic=head,
        confident=confident,
        magnitude=1.2 if head else 0.2,
        reason="test",
    )
    neutral = Evidence(False, True, 0.2, "test")
    return PostureEvidence(head=item, shoulders=neutral, torso=neutral)


def test_issue_progress_is_an_immutable_public_contract() -> None:
    progress = IssueProgress(
        problematic_seconds=4.0,
        corrected_seconds=0.0,
        next_transition_seconds=1.0,
    )

    assert progress.problematic_seconds == 4.0
    with pytest.raises(AttributeError):
        progress.problematic_seconds = 5.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("now", "problematic", "next_transition"),
    [
        (0.0, 0.0, 5.0),
        (4.0, 4.0, 1.0),
        (5.0, 5.0, 10.0),
        (14.0, 14.0, 1.0),
        (15.0, 15.0, None),
    ],
)
def test_state_machine_reports_exact_problem_progress(
    now: float,
    problematic: float,
    next_transition: float | None,
) -> None:
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = now
    machine.update(evidence(head=True), pose_present=True)
    progress = machine.progress().head

    assert progress.problematic_seconds == pytest.approx(problematic)
    if next_transition is None:
        assert progress.next_transition_seconds is None
    else:
        assert progress.next_transition_seconds == pytest.approx(next_transition)
    assert progress.corrected_seconds == 0.0


def test_progress_reports_recovery_and_excludes_tracking_pause() -> None:
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)
    clock.now = 5.0
    machine.update(evidence(head=True), pose_present=True)

    clock.now = 6.0
    machine.update(evidence(head=True), pose_present=False)
    clock.now = 6.5
    machine.update(evidence(head=True), pose_present=True)
    assert machine.progress().head.problematic_seconds == pytest.approx(6.0)

    clock.now = 7.0
    machine.update(evidence(head=False), pose_present=True)
    clock.now = 8.0
    machine.update(evidence(head=False), pose_present=True)
    progress = machine.progress().head

    assert progress.problematic_seconds == 0.0
    assert progress.corrected_seconds == pytest.approx(1.0)
    assert progress.next_transition_seconds == pytest.approx(1.0)
