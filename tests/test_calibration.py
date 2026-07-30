from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from posturely.core.calibration import (
    Baseline,
    BaselineStore,
    CalibrationError,
    CalibrationMode,
    CalibrationSession,
)
from posturely.core.types import (
    HeadFeatures,
    PostureFeatures,
    ShoulderFeatures,
    TorsoFeatures,
)

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class FakeClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now


def features(
    *,
    head_offset: float = 0.05,
    neck_angle: float = 4.0,
    line_angle: float = 1.0,
    asymmetry: float = 0.02,
    elbow_inset: float = 0.05,
    width_to_torso: float = 0.6,
    lean: float = 2.0,
    compression: float = 1.6,
) -> PostureFeatures:
    return PostureFeatures(
        head=HeadFeatures(
            horizontal_offset=head_offset,
            neck_angle_degrees=neck_angle,
        ),
        shoulders=ShoulderFeatures(
            line_angle_degrees=line_angle,
            asymmetry=asymmetry,
            elbow_inset=elbow_inset,
            width_to_torso=width_to_torso,
        ),
        torso=TorsoFeatures(lean_degrees=lean, compression=compression),
    )


def incomplete_features() -> PostureFeatures:
    return PostureFeatures(head=None, shoulders=None, torso=None)


def completed_session(
    mode: CalibrationMode,
    clock: FakeClock,
    **overrides: float,
) -> Baseline:
    session = CalibrationSession(mode, clock=clock)
    for step in range(5):
        clock.now = step * 1.25
        session.add_sample(features(**overrides))
    clock.now = 5.0
    return session.finish()


def test_stable_five_second_capture_returns_median_baseline() -> None:
    """Small jitter over five seconds must collapse to per-feature medians."""
    clock = FakeClock()
    session = CalibrationSession(CalibrationMode.SEATED, clock=clock)
    for index, offset in enumerate((0.04, 0.06, 0.05, 0.07, 0.05)):
        clock.now = index * 1.25
        session.add_sample(features(head_offset=offset))

    clock.now = 5.0
    baseline = session.finish()

    assert baseline.mode is CalibrationMode.SEATED
    assert baseline.features["head.horizontal_offset"] == pytest.approx(0.05)
    assert baseline.features["torso.compression"] == pytest.approx(1.6)
    assert baseline.captured_at == pytest.approx(5.0)


def test_capture_requires_five_seconds_of_stable_samples() -> None:
    """Finishing early would calibrate against an unrepresentative moment."""
    clock = FakeClock()
    session = CalibrationSession(CalibrationMode.SEATED, clock=clock)
    for step in range(4):
        clock.now = float(step)
        session.add_sample(features())

    clock.now = 4.999
    with pytest.raises(CalibrationError):
        session.finish()


def test_incomplete_samples_are_rejected_but_do_not_poison_capture() -> None:
    """Low-confidence frames must be skipped, never averaged into a baseline."""
    clock = FakeClock()
    session = CalibrationSession(CalibrationMode.SEATED, clock=clock)

    assert session.add_sample(incomplete_features()) is False
    for step in range(5):
        clock.now = step * 1.25
        assert session.add_sample(features()) is True

    clock.now = 5.0
    baseline = session.finish()
    assert baseline.features["head.horizontal_offset"] == pytest.approx(0.05)


def test_capture_with_only_incomplete_samples_fails() -> None:
    """A baseline built entirely from unreliable frames would be fiction."""
    clock = FakeClock()
    session = CalibrationSession(CalibrationMode.SEATED, clock=clock)
    for step in range(5):
        clock.now = step * 1.25
        session.add_sample(incomplete_features())

    clock.now = 5.0
    with pytest.raises(CalibrationError):
        session.finish()


def test_unstable_capture_is_rejected() -> None:
    """Wildly swinging geometry means the user was moving, not calibrating."""
    clock = FakeClock()
    session = CalibrationSession(CalibrationMode.SEATED, clock=clock)
    for index, offset in enumerate((0.0, 0.5, 0.0, 0.5, 0.0)):
        clock.now = index * 1.25
        session.add_sample(features(head_offset=offset))

    clock.now = 5.0
    with pytest.raises(CalibrationError):
        session.finish()


def test_seated_and_standing_baselines_are_kept_separate() -> None:
    """Calibrating one mode must never overwrite the other."""
    clock = FakeClock()
    store = BaselineStore()
    store.set(completed_session(CalibrationMode.SEATED, clock, compression=1.6))
    store.set(completed_session(CalibrationMode.STANDING, clock, compression=2.4))

    seated = store.get(CalibrationMode.SEATED)
    standing = store.get(CalibrationMode.STANDING)

    assert seated is not None
    assert standing is not None
    assert seated.features["torso.compression"] == pytest.approx(1.6)
    assert standing.features["torso.compression"] == pytest.approx(2.4)


def test_select_returns_baseline_closest_to_current_features() -> None:
    """The active baseline should match the user's current working mode."""
    clock = FakeClock()
    store = BaselineStore()
    store.set(completed_session(CalibrationMode.SEATED, clock, compression=1.6))
    store.set(completed_session(CalibrationMode.STANDING, clock, compression=2.4))

    chosen = store.select(features(compression=2.3))

    assert chosen is not None
    assert chosen.mode is CalibrationMode.STANDING


def test_select_without_baselines_returns_none() -> None:
    """Generic thresholds remain the fallback when nothing is calibrated."""
    assert BaselineStore().select(features()) is None


def test_json_round_trip_at_explicit_path_contains_only_numeric_features(
    tmp_path: Path,
) -> None:
    """Persistence must never leak landmarks, frames, or image-like fields."""
    clock = FakeClock()
    store = BaselineStore()
    store.set(completed_session(CalibrationMode.SEATED, clock))
    store.set(completed_session(CalibrationMode.STANDING, clock, compression=2.4))
    path = tmp_path / "calibration.json"

    store.save(path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert set(payload) == {"schema_version", "baselines"}
    assert payload["schema_version"] == 1
    assert len(payload["baselines"]) == 2
    for entry in payload["baselines"]:
        assert set(entry) == {"mode", "features", "captured_at"}
        assert entry["mode"] in ("seated", "standing")
        assert isinstance(entry["captured_at"], int | float)
        assert entry["features"]
        for key, value in entry["features"].items():
            assert isinstance(key, str)
            assert isinstance(value, int | float)
            assert not isinstance(value, bool)

    restored = BaselineStore.load(path)
    assert restored.get(CalibrationMode.SEATED) == store.get(CalibrationMode.SEATED)
    assert restored.get(CalibrationMode.STANDING) == store.get(CalibrationMode.STANDING)


def test_clear_removes_all_baselines(tmp_path: Path) -> None:
    """Clearing must leave no calibrated mode behind, in memory or on disk."""
    clock = FakeClock()
    store = BaselineStore()
    store.set(completed_session(CalibrationMode.SEATED, clock))
    store.set(completed_session(CalibrationMode.STANDING, clock, compression=2.4))
    path = tmp_path / "calibration.json"
    store.save(path)

    store.clear()
    store.save(path)

    assert store.get(CalibrationMode.SEATED) is None
    assert store.get(CalibrationMode.STANDING) is None
    assert store.select(features()) is None
    reloaded = BaselineStore.load(path)
    assert reloaded.get(CalibrationMode.SEATED) is None
    assert reloaded.get(CalibrationMode.STANDING) is None
