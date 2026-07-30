"""Application wiring: drive the real core engine and report state changes."""

from __future__ import annotations

import sys
from dataclasses import replace
from typing import TextIO

from posturely.calibration_runtime import CalibrationController
from posturely.core.analysis import (
    AnalysisSnapshot,
    CalibrationPhase,
    CalibrationStatus,
)
from posturely.core.evaluator import PostureEvaluator
from posturely.core.features import extract_features
from posturely.core.mode import DeskMode, ModeEstimator
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

    def __init__(
        self,
        out: TextIO | None = None,
        *,
        calibration: CalibrationController | None = None,
        mode_estimator: ModeEstimator | None = None,
    ) -> None:
        self._out = out if out is not None else sys.stdout
        self._now = 0.0
        self._evaluator = PostureEvaluator()
        self._machine = PostureStateMachine(clock=lambda: self._now)
        self._calibration = calibration
        self._mode_estimator = mode_estimator or ModeEstimator()
        self._previous = OutputState(
            head=DiagnosticColor.OFF,
            shoulders=DiagnosticColor.OFF,
            torso=DiagnosticColor.OFF,
            monitoring=MonitoringState.HEALTHY,
        )
        empty_features = PostureFeatures(head=None, shoulders=None, torso=None)
        self._snapshot = AnalysisSnapshot(
            state=self._previous,
            features=empty_features,
            evidence=self._evaluator.evaluate(empty_features),
            progress=self._machine.progress(),
            mode=DeskMode.GENERIC,
            baseline_mode=None,
            calibration=self._calibration_status(),
        )

    @property
    def snapshot(self) -> AnalysisSnapshot:
        return self._snapshot

    def process(self, frame: PoseFrame | None, now: float) -> OutputState:
        """Advance the engine with one frame and print any category changes."""
        self._now = now
        features = (
            extract_features(frame)
            if frame is not None
            else PostureFeatures(head=None, shoulders=None, torso=None)
        )
        mode = self._mode_estimator.update(frame)
        if self._calibration is not None:
            self._calibration.update(features, now)
            baseline = self._calibration.active_baseline(mode)
        else:
            baseline = None
        evidence = self._evaluator.evaluate(features, baseline=baseline)
        state = self._machine.update(evidence, pose_present=frame is not None)
        self._snapshot = AnalysisSnapshot(
            state=state,
            features=features,
            evidence=evidence,
            progress=self._machine.progress(),
            mode=mode,
            baseline_mode=mode if baseline is not None else None,
            calibration=self._calibration_status(),
        )
        self._report(state)
        return state

    def handle_command(self, key: int, now: float) -> bool:
        """Apply calibration commands without depending on a presentation layer."""
        if self._calibration is None:
            return False
        normalized = chr(key).lower() if 0 <= key <= 255 else ""
        if normalized == "c":
            self._calibration.start(self._snapshot.mode, now)
        elif normalized == "1":
            self._calibration.choose_mode(DeskMode.SEATED, now)
        elif normalized == "2":
            self._calibration.choose_mode(DeskMode.STANDING, now)
        elif normalized == "x":
            self._calibration.request_clear(now)
        else:
            return False
        self._snapshot = replace(
            self._snapshot,
            calibration=self._calibration.status,
        )
        return True

    def _calibration_status(self) -> CalibrationStatus:
        if self._calibration is not None:
            return self._calibration.status
        return CalibrationStatus(
            CalibrationPhase.IDLE,
            None,
            0.0,
            "generic thresholds",
        )

    def _report(self, state: OutputState) -> None:
        for category in _CATEGORIES:
            old = getattr(self._previous, category)
            new = getattr(state, category)
            if new is not old:
                print(f"{category}: {old.value} -> {new.value}", file=self._out)
        self._previous = state
