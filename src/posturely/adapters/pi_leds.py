"""Raspberry Pi LED output adapter with lazy GPIO imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from posturely.core.analysis import AnalysisSnapshot, CalibrationPhase
from posturely.core.types import DiagnosticColor, MonitoringState

_RGB = tuple[float, float, float]
_COLOR: dict[DiagnosticColor, _RGB] = {
    DiagnosticColor.OFF: (0.0, 0.0, 0.0),
    DiagnosticColor.AMBER: (1.0, 0.45, 0.0),
    DiagnosticColor.RED: (1.0, 0.0, 0.0),
}


class PiLedOutput:
    """Drive three RGB diagnostics and one dim monitoring LED."""

    HEAD_PINS = (17, 27, 22)
    SHOULDERS_PINS = (5, 6, 13)
    TORSO_PINS = (19, 26, 21)
    MONITOR_PIN = 20
    BUTTON_PIN = 16

    def __init__(
        self,
        *,
        rgb_factory: Callable[[int, int, int], Any] | None = None,
        monitor_factory: Callable[[int], Any] | None = None,
    ) -> None:
        if rgb_factory is None or monitor_factory is None:
            try:
                from gpiozero import PWMLED, RGBLED
            except ImportError as exc:
                raise RuntimeError(
                    "Pi LED output requires gpiozero on Raspberry Pi"
                ) from exc
            if rgb_factory is None:
                def create_rgb(red: int, green: int, blue: int) -> Any:
                    return RGBLED(
                        red=red,
                        green=green,
                        blue=blue,
                        active_high=True,
                    )

                rgb_factory = create_rgb
            if monitor_factory is None:
                monitor_factory = PWMLED
        self._diagnostics = [
            rgb_factory(*self.HEAD_PINS),
            rgb_factory(*self.SHOULDERS_PINS),
            rgb_factory(*self.TORSO_PINS),
        ]
        self._monitor = monitor_factory(self.MONITOR_PIN)

    def apply(self, snapshot: AnalysisSnapshot, now: float) -> None:
        if snapshot.calibration.phase is CalibrationPhase.CAPTURING:
            blue = 0.5 if int(now * 4) % 2 == 0 else 0.1
            colors = [(0.0, 0.0, blue)] * 3
        else:
            colors = [
                _COLOR[snapshot.state.head],
                _COLOR[snapshot.state.shoulders],
                _COLOR[snapshot.state.torso],
            ]
        for light, color in zip(self._diagnostics, colors, strict=True):
            light.color = color
        self._monitor.value = _monitor_value(snapshot.state.monitoring, now)

    def close(self) -> None:
        for light in self._diagnostics:
            light.color = _COLOR[DiagnosticColor.OFF]
            light.close()
        self._monitor.value = 0.0
        self._monitor.close()


def _monitor_value(state: MonitoringState, now: float) -> float:
    if state is MonitoringState.HEALTHY:
        return 0.12
    if state is MonitoringState.WAITING:
        return 0.12 if int(now) % 2 == 0 else 0.0
    return 0.3 if int(now * 4) % 2 == 0 else 0.0
