from __future__ import annotations

import io
from typing import Any

from posturely.core.analysis import AnalysisSnapshot
from posturely.core.mode import DeskMode
from posturely.core.types import DiagnosticColor, MonitoringState, OutputState
from posturely.demo_ui import run_visual_demo


class FakeFrame:
    shape = (480, 640, 3)


class RecordingPreview:
    def __init__(self) -> None:
        self.states: list[OutputState] = []
        self.snapshots: list[AnalysisSnapshot] = []
        self.closed = False

    def render(self, **kwargs: Any) -> int:
        self.states.append(kwargs["state"])
        self.snapshots.append(kwargs["snapshot"])
        return -1

    def close(self) -> None:
        self.closed = True


def test_visual_demo_cycles_every_light_without_a_camera() -> None:
    """The automatic visual demo must prove every appliance light can fire."""
    preview = RecordingPreview()
    frames_created = 0

    def frame_factory() -> FakeFrame:
        nonlocal frames_created
        frames_created += 1
        return FakeFrame()

    result = run_visual_demo(
        seconds=70.0,
        speed=10.0,
        mirror=True,
        out=io.StringIO(),
        preview_factory=lambda: preview,
        frame_factory=frame_factory,
        sleep=lambda _: None,
    )

    assert result == 0
    assert frames_created == len(preview.states)
    for category in ("head", "shoulders", "torso"):
        colors = {getattr(state, category) for state in preview.states}
        assert DiagnosticColor.AMBER in colors
        assert DiagnosticColor.RED in colors
    monitoring = {state.monitoring for state in preview.states}
    assert MonitoringState.HEALTHY in monitoring
    assert MonitoringState.WAITING in monitoring
    assert {snapshot.mode for snapshot in preview.snapshots} >= {
        DeskMode.SEATED,
        DeskMode.STANDING,
    }
    assert any(
        snapshot.progress.head.next_transition_seconds == 1.0
        for snapshot in preview.snapshots
    )
    assert all(
        snapshot.state == state
        for snapshot, state in zip(preview.snapshots, preview.states, strict=True)
    )
    assert all(
        snapshot.evidence.head.magnitude >= 0.0 for snapshot in preview.snapshots
    )
    assert preview.closed


def test_visual_demo_quits_and_closes_on_escape() -> None:
    """Closing the simulation must release its window without finishing the timeline."""

    class EscapePreview(RecordingPreview):
        def render(self, **kwargs: Any) -> int:
            super().render(**kwargs)
            return 27

    preview = EscapePreview()

    result = run_visual_demo(
        seconds=70.0,
        speed=10.0,
        mirror=True,
        out=io.StringIO(),
        preview_factory=lambda: preview,
        frame_factory=FakeFrame,
        sleep=lambda _: None,
    )

    assert result == 0
    assert len(preview.states) == 1
    assert preview.closed
