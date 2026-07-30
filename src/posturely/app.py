"""Application wiring: drive the real core engine and report state changes."""

from __future__ import annotations

import sys
from typing import TextIO

from posturely.core.evaluator import PostureEvaluator
from posturely.core.features import extract_features
from posturely.core.state_machine import PostureStateMachine
from posturely.core.types import (
    DiagnosticColor,
    MonitoringState,
    OutputState,
    PoseFrame,
    PostureFeatures,
)

_CATEGORIES = ("head", "shoulders", "torso", "monitoring")


class PostureApplication:
    """Feed pose frames through features -> evaluator -> state machine."""

    def __init__(self, out: TextIO | None = None) -> None:
        self._out = out if out is not None else sys.stdout
        self._now = 0.0
        self._evaluator = PostureEvaluator()
        self._machine = PostureStateMachine(clock=lambda: self._now)
        self._previous = OutputState(
            head=DiagnosticColor.OFF,
            shoulders=DiagnosticColor.OFF,
            torso=DiagnosticColor.OFF,
            monitoring=MonitoringState.HEALTHY,
        )

    def process(self, frame: PoseFrame | None, now: float) -> OutputState:
        """Advance the engine with one frame and print any category changes."""
        self._now = now
        features = (
            extract_features(frame)
            if frame is not None
            else PostureFeatures(head=None, shoulders=None, torso=None)
        )
        evidence = self._evaluator.evaluate(features)
        state = self._machine.update(evidence, pose_present=frame is not None)
        self._report(state)
        return state

    def _report(self, state: OutputState) -> None:
        for category in _CATEGORIES:
            old = getattr(self._previous, category)
            new = getattr(state, category)
            if new is not old:
                print(f"{category}: {old.value} -> {new.value}", file=self._out)
        self._previous = state
