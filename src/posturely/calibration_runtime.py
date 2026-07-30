"""Runtime orchestration for optional, numeric-only posture calibration."""

from __future__ import annotations

from pathlib import Path

from posturely.core.analysis import CalibrationPhase, CalibrationStatus
from posturely.core.calibration import (
    Baseline,
    BaselineStore,
    CalibrationError,
    CalibrationMode,
    CalibrationSession,
)
from posturely.core.mode import DeskMode
from posturely.core.types import PostureFeatures

_CAPTURE_SECONDS = 5.0
_CLEAR_CONFIRM_SECONDS = 3.0


class CalibrationController:
    """Connect capture sessions and safe persistence to runtime commands."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._store = BaselineStore()
        self._session: CalibrationSession | None = None
        self._started_at: float | None = None
        self._now = 0.0
        self._clear_requested_at: float | None = None
        self._status = CalibrationStatus(
            CalibrationPhase.IDLE,
            None,
            0.0,
            "generic thresholds",
        )
        if path.exists():
            try:
                self._store = BaselineStore.load(path)
            except CalibrationError as exc:
                self._status = CalibrationStatus(
                    CalibrationPhase.FAILED,
                    None,
                    0.0,
                    str(exc),
                )

    @property
    def status(self) -> CalibrationStatus:
        return self._status

    def start(self, mode: DeskMode, now: float) -> None:
        if mode is DeskMode.GENERIC:
            self._session = None
            self._started_at = None
            self._status = CalibrationStatus(
                CalibrationPhase.NEEDS_MODE,
                None,
                0.0,
                "press 1 for seated or 2 for standing",
            )
            return
        self._begin(mode, now)

    def choose_mode(self, mode: DeskMode, now: float) -> None:
        if mode is DeskMode.GENERIC:
            raise ValueError("calibration mode must be seated or standing")
        self._begin(mode, now)

    def update(self, features: PostureFeatures, now: float) -> None:
        if self._session is None or self._started_at is None:
            return
        self._now = now
        self._session.add_sample(features)
        elapsed = max(0.0, now - self._started_at)
        progress = min(1.0, elapsed / _CAPTURE_SECONDS)
        mode = self._status.mode
        self._status = CalibrationStatus(
            CalibrationPhase.CAPTURING,
            mode,
            progress,
            f"hold comfortable posture: {progress:.0%}",
        )
        if elapsed < _CAPTURE_SECONDS:
            return
        try:
            baseline = self._session.finish()
            self._store.set(baseline)
            self._store.save(self._path)
        except (CalibrationError, OSError) as exc:
            self._status = CalibrationStatus(
                CalibrationPhase.FAILED,
                mode,
                progress,
                str(exc),
            )
        else:
            self._status = CalibrationStatus(
                CalibrationPhase.SUCCEEDED,
                mode,
                1.0,
                f"{mode.value if mode else 'posture'} baseline saved",
            )
        finally:
            self._session = None
            self._started_at = None

    def request_clear(self, now: float) -> None:
        if (
            self._clear_requested_at is not None
            and now - self._clear_requested_at <= _CLEAR_CONFIRM_SECONDS
        ):
            self._store.clear()
            self._store.save(self._path)
            self._clear_requested_at = None
            self._status = CalibrationStatus(
                CalibrationPhase.SUCCEEDED,
                None,
                1.0,
                "all calibration cleared",
            )
            return
        self._clear_requested_at = now
        self._status = CalibrationStatus(
            CalibrationPhase.CONFIRM_CLEAR,
            None,
            0.0,
            "press x again within 3 seconds to clear calibration",
        )

    def active_baseline(self, mode: DeskMode) -> Baseline | None:
        if mode is DeskMode.GENERIC:
            return None
        return self._store.get(CalibrationMode(mode.value))

    def _begin(self, mode: DeskMode, now: float) -> None:
        calibration_mode = CalibrationMode(mode.value)
        self._now = now
        self._session = CalibrationSession(
            calibration_mode,
            clock=lambda: self._now,
        )
        self._started_at = now
        self._clear_requested_at = None
        self._status = CalibrationStatus(
            CalibrationPhase.CAPTURING,
            mode,
            0.0,
            "hold a comfortable upright posture",
        )
