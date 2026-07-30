from __future__ import annotations

from pathlib import Path

import pytest

from posturely.calibration_runtime import CalibrationController
from posturely.core.analysis import CalibrationPhase
from posturely.core.calibration import Baseline, BaselineStore, CalibrationMode
from posturely.core.mode import DeskMode
from posturely.core.types import (
    HeadFeatures,
    PostureFeatures,
    ShoulderFeatures,
    TorsoFeatures,
)


def features(
    *,
    head_offset: float = 0.05,
    complete: bool = True,
) -> PostureFeatures:
    if not complete:
        return PostureFeatures(head=None, shoulders=None, torso=None)
    return PostureFeatures(
        head=HeadFeatures(head_offset, 4.0),
        shoulders=ShoulderFeatures(1.0, 0.02, 0.05, 0.6),
        torso=TorsoFeatures(2.0, 1.6),
    )


def seed(path: Path, *, offset: float = 0.05) -> Baseline:
    baseline = Baseline(
        mode=CalibrationMode.SEATED,
        features={
            "head.horizontal_offset": offset,
            "head.neck_angle_degrees": 4.0,
            "shoulders.line_angle_degrees": 1.0,
            "shoulders.asymmetry": 0.02,
            "shoulders.elbow_inset": 0.05,
            "shoulders.width_to_torso": 0.6,
            "torso.lean_degrees": 2.0,
            "torso.compression": 1.6,
        },
        captured_at=1.0,
    )
    store = BaselineStore()
    store.set(baseline)
    store.save(path)
    return baseline


def complete_capture(
    controller: CalibrationController,
    *,
    offsets: tuple[float, ...] = (0.04, 0.06, 0.05, 0.07, 0.05, 0.05),
) -> None:
    for now, offset in zip((0.0, 1.0, 2.0, 3.0, 4.0, 5.0), offsets, strict=True):
        controller.update(features(head_offset=offset), now)


def test_generic_start_requires_an_explicit_mode(tmp_path: Path) -> None:
    controller = CalibrationController(tmp_path / "calibration.json")

    controller.start(DeskMode.GENERIC, 0.0)

    assert controller.status.phase is CalibrationPhase.NEEDS_MODE
    assert controller.status.mode is None


def test_mode_choice_and_five_seconds_save_a_numeric_baseline(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    controller = CalibrationController(path)
    controller.start(DeskMode.GENERIC, 0.0)

    controller.choose_mode(DeskMode.SEATED, 0.0)
    complete_capture(controller)

    assert controller.status.phase is CalibrationPhase.SUCCEEDED
    assert controller.status.mode is DeskMode.SEATED
    assert controller.status.progress == pytest.approx(1.0)
    baseline = controller.active_baseline(DeskMode.SEATED)
    assert baseline is not None
    assert baseline.features["head.horizontal_offset"] == pytest.approx(0.05)
    assert BaselineStore.load(path).get(CalibrationMode.SEATED) == baseline
    assert "landmark" not in path.read_text(encoding="utf-8").lower()


def test_failed_capture_preserves_the_previous_baseline(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    previous = seed(path, offset=0.12)
    controller = CalibrationController(path)
    controller.start(DeskMode.SEATED, 0.0)

    for now in (0.0, 1.0, 2.0, 3.0, 4.0, 5.0):
        controller.update(features(complete=False), now)

    assert controller.status.phase is CalibrationPhase.FAILED
    assert controller.active_baseline(DeskMode.SEATED) == previous
    assert BaselineStore.load(path).get(CalibrationMode.SEATED) == previous


def test_unstable_capture_is_rejected_without_replacing_data(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    previous = seed(path)
    controller = CalibrationController(path)
    controller.start(DeskMode.SEATED, 0.0)

    complete_capture(controller, offsets=(0.0, 0.5, 0.0, 0.5, 0.0, 0.5))

    assert controller.status.phase is CalibrationPhase.FAILED
    assert "unstable" in controller.status.message
    assert controller.active_baseline(DeskMode.SEATED) == previous


def test_clear_requires_a_second_request_within_three_seconds(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    seed(path)
    controller = CalibrationController(path)

    controller.request_clear(10.0)
    assert controller.status.phase is CalibrationPhase.CONFIRM_CLEAR
    assert controller.active_baseline(DeskMode.SEATED) is not None

    controller.request_clear(12.9)
    assert controller.status.phase is CalibrationPhase.SUCCEEDED
    assert controller.active_baseline(DeskMode.SEATED) is None
    assert BaselineStore.load(path).get(CalibrationMode.SEATED) is None


def test_expired_clear_confirmation_preserves_data(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    seed(path)
    controller = CalibrationController(path)

    controller.request_clear(10.0)
    controller.request_clear(13.1)

    assert controller.status.phase is CalibrationPhase.CONFIRM_CLEAR
    assert controller.active_baseline(DeskMode.SEATED) is not None


def test_invalid_json_warns_and_keeps_generic_operation(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    path.write_text("{bad json", encoding="utf-8")

    controller = CalibrationController(path)

    assert controller.status.phase is CalibrationPhase.FAILED
    assert "cannot read" in controller.status.message
    assert controller.active_baseline(DeskMode.SEATED) is None
    assert path.read_text(encoding="utf-8") == "{bad json"
