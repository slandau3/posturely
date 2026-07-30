from __future__ import annotations

from dataclasses import replace

from posturely.adapters.pi_leds import PiLedOutput
from posturely.core.analysis import (
    AnalysisSnapshot,
    CalibrationPhase,
    CalibrationStatus,
    DiagnosticProgress,
    IssueProgress,
)
from posturely.core.mode import DeskMode
from posturely.core.types import (
    DiagnosticColor,
    Evidence,
    MonitoringState,
    OutputState,
    PostureEvidence,
    PostureFeatures,
)
from posturely.outputs import PostureOutput


class FakeRgb:
    def __init__(self, pins: tuple[int, int, int]) -> None:
        self.pins = pins
        self.color = (0.0, 0.0, 0.0)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeLed:
    def __init__(self, pin: int) -> None:
        self.pin = pin
        self.value = 0.0
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _snapshot(
    *,
    head_color: DiagnosticColor = DiagnosticColor.OFF,
) -> AnalysisSnapshot:
    neutral = Evidence(False, True, 0.2, "acceptable")
    progress = IssueProgress(0.0, 0.0, None)
    return AnalysisSnapshot(
        state=OutputState(
            head_color,
            DiagnosticColor.OFF,
            DiagnosticColor.OFF,
            MonitoringState.HEALTHY,
        ),
        features=PostureFeatures(None, None, None),
        evidence=PostureEvidence(neutral, neutral, neutral),
        progress=DiagnosticProgress(progress, progress, progress),
        mode=DeskMode.GENERIC,
        baseline_mode=None,
        calibration=CalibrationStatus(
            CalibrationPhase.IDLE,
            None,
            0.0,
            "generic thresholds",
        ),
    )


def test_pi_output_satisfies_portable_protocol_and_maps_diagnostics() -> None:
    rgbs: list[FakeRgb] = []
    monitor = FakeLed(20)

    def rgb_factory(red: int, green: int, blue: int) -> FakeRgb:
        light = FakeRgb((red, green, blue))
        rgbs.append(light)
        return light

    output: PostureOutput = PiLedOutput(
        rgb_factory=rgb_factory,
        monitor_factory=lambda _pin: monitor,
    )
    analysis = _snapshot(head_color=DiagnosticColor.AMBER)
    analysis = replace(
        analysis,
        state=replace(
            analysis.state,
            shoulders=DiagnosticColor.RED,
            torso=DiagnosticColor.OFF,
        ),
    )

    output.apply(analysis, 0.0)

    assert [light.color for light in rgbs] == [
        (1.0, 0.45, 0.0),
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    ]
    assert monitor.value == 0.12


def test_monitoring_patterns_and_calibration_blue_override() -> None:
    rgbs: list[FakeRgb] = []
    monitor = FakeLed(20)
    output = PiLedOutput(
        rgb_factory=lambda *pins: rgbs.append(FakeRgb(pins)) or rgbs[-1],
        monitor_factory=lambda _pin: monitor,
    )
    analysis = _snapshot()

    output.apply(
        replace(analysis, state=replace(analysis.state, monitoring=MonitoringState.WAITING)),
        1.1,
    )
    waiting_value = monitor.value
    output.apply(
        replace(analysis, state=replace(analysis.state, monitoring=MonitoringState.FAULT)),
        1.1,
    )
    fault_value = monitor.value
    capturing = replace(
        analysis,
        calibration=CalibrationStatus(
            CalibrationPhase.CAPTURING,
            DeskMode.SEATED,
            0.5,
            "capturing",
        ),
    )
    output.apply(capturing, 0.0)

    assert waiting_value in (0.0, 0.12)
    assert fault_value in (0.0, 0.3)
    assert waiting_value != fault_value
    assert [light.color for light in rgbs] == [(0.0, 0.0, 0.5)] * 3


def test_pi_output_closes_every_light_off() -> None:
    rgbs: list[FakeRgb] = []
    monitor = FakeLed(20)
    output = PiLedOutput(
        rgb_factory=lambda *pins: rgbs.append(FakeRgb(pins)) or rgbs[-1],
        monitor_factory=lambda _pin: monitor,
    )
    output.apply(_snapshot(head_color=DiagnosticColor.RED), 0.0)

    output.close()

    assert all(light.color == (0.0, 0.0, 0.0) and light.closed for light in rgbs)
    assert monitor.value == 0.0
    assert monitor.closed
