from __future__ import annotations

from pathlib import Path

import pytest

from posturely.adapters.demo_pose import demo_frame
from posturely.app import PostureApplication
from posturely.calibration_runtime import CalibrationController
from posturely.core.analysis import CalibrationPhase
from posturely.core.calibration import Baseline, BaselineStore, CalibrationMode
from posturely.core.mode import DeskMode, ModeEstimator
from posturely.core.types import DiagnosticColor


def test_application_publishes_one_complete_immutable_snapshot() -> None:
    app = PostureApplication()
    frame = demo_frame(10.0)

    state = app.process(frame, 10.0)
    snapshot = app.snapshot

    assert snapshot.state == state
    assert snapshot.features.head is not None
    assert snapshot.evidence.head.problematic
    assert snapshot.evidence.head.magnitude >= 1.0
    assert snapshot.progress.head.problematic_seconds == 0.0
    assert snapshot.mode is DeskMode.GENERIC
    with pytest.raises(AttributeError):
        snapshot.mode = DeskMode.SEATED  # type: ignore[misc]


def test_application_selects_matching_calibrated_baseline(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    store = BaselineStore()
    store.set(
        Baseline(
            CalibrationMode.SEATED,
            {
                "head.horizontal_offset": 0.45,
                "head.neck_angle_degrees": 24.0,
                "shoulders.line_angle_degrees": 0.0,
                "shoulders.asymmetry": 0.0,
                "shoulders.elbow_inset": -0.2,
                "shoulders.width_to_torso": 0.67,
                "torso.lean_degrees": 0.0,
                "torso.compression": 1.5,
            },
            1.0,
        )
    )
    store.save(path)
    estimator = ModeEstimator()
    estimator.override(DeskMode.SEATED)
    app = PostureApplication(
        calibration=CalibrationController(path),
        mode_estimator=estimator,
    )

    state = app.process(demo_frame(10.0), 10.0)

    assert app.snapshot.baseline_mode is DeskMode.SEATED
    assert app.snapshot.evidence.head.magnitude < 0.05
    assert state.head is DiagnosticColor.OFF


def test_application_commands_drive_calibration_without_ui_dependencies(
    tmp_path: Path,
) -> None:
    app = PostureApplication(
        calibration=CalibrationController(tmp_path / "calibration.json")
    )
    app.process(demo_frame(0.0), 0.0)

    assert app.handle_command(ord("c"), 0.0)
    assert app.snapshot.calibration.phase is CalibrationPhase.NEEDS_MODE
    assert app.handle_command(ord("1"), 0.1)
    assert app.snapshot.calibration.phase is CalibrationPhase.CAPTURING
    assert app.snapshot.calibration.mode is DeskMode.SEATED

    assert app.handle_command(ord("x"), 1.0)
    assert app.snapshot.calibration.phase is CalibrationPhase.CONFIRM_CLEAR
    assert app.handle_command(ord("x"), 2.0)
    assert app.snapshot.calibration.phase is CalibrationPhase.SUCCEEDED
    assert "cleared" in app.snapshot.calibration.message


def test_unknown_application_command_is_not_consumed() -> None:
    app = PostureApplication()
    app.process(demo_frame(0.0), 0.0)

    assert not app.handle_command(ord("z"), 0.0)
