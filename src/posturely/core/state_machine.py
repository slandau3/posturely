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


@dataclass(slots=True)
class _IssueTimer:
    problem_since: float | None = None
    corrected_since: float | None = None
    color: DiagnosticColor = DiagnosticColor.OFF

    def update(self, evidence: Evidence | None, now: float) -> DiagnosticColor:
        if evidence is None or not evidence.confident:
            self.reset()
            return self.color

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
        self.color = DiagnosticColor.OFF


class PostureStateMachine:
    """Maintain one independent alert timer for each diagnostic category."""

    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._head = _IssueTimer()
        self._shoulders = _IssueTimer()
        self._torso = _IssueTimer()

    def update(
        self,
        evidence: PostureEvidence,
        *,
        pose_present: bool,
        fault: str | None = None,
    ) -> OutputState:
        now = self._clock()
        if fault is not None:
            self._reset_diagnostics()
            return self._output(MonitoringState.FAULT)
        if not pose_present:
            self._reset_diagnostics()
            return self._output(MonitoringState.WAITING)

        self._head.update(evidence.head, now)
        self._shoulders.update(evidence.shoulders, now)
        self._torso.update(evidence.torso, now)
        return self._output(MonitoringState.HEALTHY)

    def _reset_diagnostics(self) -> None:
        self._head.reset()
        self._shoulders.reset()
        self._torso.reset()

    def _output(self, monitoring: MonitoringState) -> OutputState:
        return OutputState(
            head=self._head.color,
            shoulders=self._shoulders.color,
            torso=self._torso.color,
            monitoring=monitoring,
        )
