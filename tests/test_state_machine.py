from __future__ import annotations

from dataclasses import dataclass

import pytest

from posturely.core.state_machine import PostureStateMachine
from posturely.core.types import (
    DiagnosticColor,
    Evidence,
    MonitoringState,
    PostureEvidence,
)


@dataclass
class FakeClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now


def evidence(
    *,
    head: bool = False,
    shoulders: bool = False,
    torso: bool = False,
    confident: bool = True,
) -> PostureEvidence:
    def item(problematic: bool) -> Evidence:
        return Evidence(
            problematic=problematic,
            confident=confident,
            magnitude=1.2 if problematic else 0.2,
            reason="test",
        )

    return PostureEvidence(
        head=item(head),
        shoulders=item(shoulders),
        torso=item(torso),
    )


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        (0.0, DiagnosticColor.OFF),
        (4.999, DiagnosticColor.OFF),
        (5.0, DiagnosticColor.AMBER),
        (14.999, DiagnosticColor.AMBER),
        (15.0, DiagnosticColor.RED),
    ],
)
def test_sustained_issue_uses_exact_alert_boundaries(
    elapsed: float,
    expected: DiagnosticColor,
) -> None:
    """Changing a timing boundary would violate the quiet-until-needed interaction."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = elapsed
    state = machine.update(evidence(head=True), pose_present=True)

    assert state.head is expected


def test_diagnostics_accumulate_independently() -> None:
    """Starting one issue later must not inherit another issue's timer."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = 10.0
    state = machine.update(evidence(head=True, shoulders=True), pose_present=True)

    assert state.head is DiagnosticColor.AMBER
    assert state.shoulders is DiagnosticColor.OFF

    clock.now = 15.0
    state = machine.update(evidence(head=True, shoulders=True), pose_present=True)
    assert state.head is DiagnosticColor.RED
    assert state.shoulders is DiagnosticColor.AMBER


def test_alert_remains_visible_until_two_seconds_of_correction() -> None:
    """Clearing on one good frame would make feedback flicker."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(torso=True), pose_present=True)
    clock.now = 15.0
    assert machine.update(evidence(torso=True), pose_present=True).torso is DiagnosticColor.RED

    clock.now = 15.1
    assert machine.update(evidence(), pose_present=True).torso is DiagnosticColor.RED
    clock.now = 17.099
    assert machine.update(evidence(), pose_present=True).torso is DiagnosticColor.RED
    clock.now = 17.1
    assert machine.update(evidence(), pose_present=True).torso is DiagnosticColor.OFF


def test_uncertainty_suppresses_and_resets_alerts() -> None:
    """Missing landmarks must never preserve or accumulate a bad-posture alert."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)
    clock.now = 16.0
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.RED

    clock.now = 17.0
    state = machine.update(evidence(head=True, confident=False), pose_present=True)
    assert state.head is DiagnosticColor.RED

    clock.now = 18.01
    state = machine.update(evidence(head=True, confident=False), pose_present=True)
    assert state.head is DiagnosticColor.OFF

    clock.now = 20.0
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.OFF


def test_brief_pose_loss_pauses_instead_of_resetting_issue_timer() -> None:
    """One dropped pose result must not prevent a sustained issue from alerting."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = 4.0
    state = machine.update(evidence(head=True), pose_present=False)
    assert state.monitoring is MonitoringState.HEALTHY
    clock.now = 4.5
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.OFF
    clock.now = 5.0
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.OFF
    clock.now = 5.5
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.AMBER


def test_brief_metric_uncertainty_pauses_instead_of_resetting_issue_timer() -> None:
    """A momentarily hidden ear must not erase otherwise continuous head evidence."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = 4.0
    machine.update(evidence(head=True, confident=False), pose_present=True)
    clock.now = 4.5
    machine.update(evidence(head=True), pose_present=True)
    clock.now = 5.0
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.OFF
    clock.now = 5.5
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.AMBER


def test_long_pose_loss_resets_timers_and_reports_waiting() -> None:
    """A real absence must not preserve accumulated bad-posture time."""
    clock = FakeClock()
    machine = PostureStateMachine(clock=clock)
    machine.update(evidence(head=True), pose_present=True)

    clock.now = 4.0
    machine.update(evidence(head=True), pose_present=False)
    clock.now = 5.01
    state = machine.update(evidence(head=True), pose_present=False)
    assert state.monitoring is MonitoringState.WAITING
    assert state.head is DiagnosticColor.OFF

    clock.now = 5.1
    machine.update(evidence(head=True), pose_present=True)
    clock.now = 10.09
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.OFF
    clock.now = 10.1
    assert machine.update(evidence(head=True), pose_present=True).head is DiagnosticColor.AMBER


@pytest.mark.parametrize(
    ("pose_present", "fault", "monitoring"),
    [
        (True, None, MonitoringState.HEALTHY),
        (False, None, MonitoringState.WAITING),
        (True, "camera disconnected", MonitoringState.FAULT),
    ],
)
def test_monitoring_indicator_reports_health(
    pose_present: bool,
    fault: str | None,
    monitoring: MonitoringState,
) -> None:
    """A camera/model fault must remain distinguishable from ordinary absence."""
    machine = PostureStateMachine(clock=FakeClock())

    state = machine.update(evidence(), pose_present=pose_present, fault=fault)

    assert state.monitoring is monitoring
