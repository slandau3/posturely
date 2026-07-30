"""Temporal filtering for quiet, sustained posture feedback."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic

from posturely.core.types import (
    DiagnosticColor,
    Evidence,
    MonitoringState,
    OutputState,
    PostureEvidence,
)

_TRACKING_GRACE_SECONDS = 1.0


@dataclass(slots=True)
class _IssueTimer:
    problem_since: float | None = None
    corrected_since: float | None = None
    uncertain_since: float | None = None
    color: DiagnosticColor = DiagnosticColor.OFF

    def update(self, evidence: Evidence | None, now: float) -> DiagnosticColor:
        if evidence is None or not evidence.confident:
            if self.uncertain_since is None:
                self.uncertain_since = now
            elif now - self.uncertain_since >= _TRACKING_GRACE_SECONDS:
                self.reset()
            return self.color

        self.resume(now)
        if evidence.problematic:
            self.corrected_since = None
            if self.problem_since is None:
                self.problem_since = now
            elapsed = now - self.problem_since
            if elapsed >= 15.0:
                self.color = DiagnosticColor.RED
            elif elapsed >= 5.0 and self.color is not DiagnosticColor.RED:
                self.color = DiagnosticColor.AMBER
            return self.color

        self.problem_since = None
        if self.color is DiagnosticColor.OFF:
            self.corrected_since = None
            return self.color
        if self.corrected_since is None:
            self.corrected_since = now
        if now - self.corrected_since >= 2.0:
            self.reset()
        return self.color

    def reset(self) -> None:
        self.problem_since = None
        self.corrected_since = None
        self.uncertain_since = None
        self.color = DiagnosticColor.OFF

    def pause(self, started_at: float) -> None:
        if self.uncertain_since is None:
            self.uncertain_since = started_at

    def resume(self, now: float) -> None:
        if self.uncertain_since is None:
            return
        pause_duration = now - self.uncertain_since
        if self.problem_since is not None:
            self.problem_since += pause_duration
        if self.corrected_since is not None:
            self.corrected_since += pause_duration
        self.uncertain_since = None


class PostureStateMachine:
    """Maintain one independent alert timer for each diagnostic category."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._head = _IssueTimer()
        self._shoulders = _IssueTimer()
        self._torso = _IssueTimer()
        self._pose_missing_since: float | None = None
        self._has_seen_pose = False

    def update(
        self,
        evidence: PostureEvidence,
        *,
        pose_present: bool,
        fault: str | None = None,
    ) -> OutputState:
        now = self._clock()
        if fault is not None:
            self._pose_missing_since = None
            self._reset_diagnostics()
            return self._output(MonitoringState.FAULT)
        if not pose_present:
            if not self._has_seen_pose:
                self._reset_diagnostics()
                return self._output(MonitoringState.WAITING)
            if self._pose_missing_since is None:
                self._pose_missing_since = now
                self._pause_diagnostics(now)
            if now - self._pose_missing_since < _TRACKING_GRACE_SECONDS:
                return self._output(MonitoringState.HEALTHY)
            self._reset_diagnostics()
            return self._output(MonitoringState.WAITING)

        if self._pose_missing_since is not None:
            self._resume_diagnostics(now)
        self._pose_missing_since = None
        self._has_seen_pose = True
        self._head.update(evidence.head, now)
        self._shoulders.update(evidence.shoulders, now)
        self._torso.update(evidence.torso, now)
        return self._output(MonitoringState.HEALTHY)

    def _reset_diagnostics(self) -> None:
        self._head.reset()
        self._shoulders.reset()
        self._torso.reset()

    def _pause_diagnostics(self, now: float) -> None:
        self._head.pause(now)
        self._shoulders.pause(now)
        self._torso.pause(now)

    def _resume_diagnostics(self, now: float) -> None:
        self._head.resume(now)
        self._shoulders.resume(now)
        self._torso.resume(now)

    def _output(self, monitoring: MonitoringState) -> OutputState:
        return OutputState(
            head=self._head.color,
            shoulders=self._shoulders.color,
            torso=self._torso.color,
            monitoring=monitoring,
        )
