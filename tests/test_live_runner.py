from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import pytest

from posturely.adapters.demo_pose import demo_frame
from posturely.core.types import (
    DiagnosticColor,
    MonitoringState,
    OutputState,
)
from posturely.live import RollingFps, run_live


class FakeCamera:
    def __init__(self, frames: list[object], fault: str | None = None) -> None:
        self.frames = list(frames)
        self.fault = fault
        self.closed = False

    def __enter__(self) -> FakeCamera:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def read(self) -> object | None:
        if self.frames:
            return self.frames.pop(0)
        self.fault = "end of fake stream"
        return None


class FakePose:
    def __init__(self) -> None:
        self.calls: list[tuple[object, int]] = []
        self.closed = False

    def __enter__(self) -> FakePose:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def detect(self, frame: object, timestamp_ms: int):
        self.calls.append((frame, timestamp_ms))
        return demo_frame(0.0)


class FakePreview:
    def __init__(self, key: int | list[int] | None = None) -> None:
        key = ord("q") if key is None else key
        self.keys = list(key) if isinstance(key, list) else [key]
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def __enter__(self) -> FakePreview:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def render(self, **kwargs: object) -> int:
        self.calls.append(kwargs)
        return self.keys.pop(0) if self.keys else ord("q")


def args(*, mirror: bool = True, no_preview: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        camera=0,
        model="/tmp/fake.task",
        mirror=mirror,
        no_preview=no_preview,
        calibration_file=".posturely-calibration.json",
        details=True,
        landmarks=True,
        pi_leds=False,
    )


def factories(
    camera: FakeCamera,
    pose: FakePose,
    preview: FakePreview,
) -> tuple[Callable[[int], FakeCamera], Callable[[str], FakePose], Callable[[], FakePreview]]:
    return (
        lambda _index: camera,
        lambda _path: pose,
        lambda: preview,
    )


def test_live_loop_processes_frame_renders_state_and_closes_on_q() -> None:
    frame = object()
    camera = FakeCamera([frame])
    pose = FakePose()
    preview = FakePreview()
    camera_factory, pose_factory, preview_factory = factories(camera, pose, preview)

    code = run_live(
        args(mirror=False),
        camera_factory=camera_factory,
        pose_factory=pose_factory,
        preview_factory=preview_factory,
        clock=lambda: 2.0,
    )

    assert code == 0
    assert pose.calls == [(frame, 2000)]
    assert len(preview.calls) == 1
    call = preview.calls[0]
    assert call["frame"] is frame
    assert call["pose"] == demo_frame(0.0)
    assert call["mirror"] is False
    assert camera.closed and pose.closed and preview.closed


def test_live_loop_does_not_construct_preview_in_headless_mode() -> None:
    camera = FakeCamera([object()])
    pose = FakePose()
    preview_calls = 0

    def preview_factory() -> FakePreview:
        nonlocal preview_calls
        preview_calls += 1
        return FakePreview()

    code = run_live(
        args(no_preview=True),
        camera_factory=lambda _index: camera,
        pose_factory=lambda _path: pose,
        preview_factory=preview_factory,
        clock=lambda: 1.0,
    )

    assert code == 1
    assert preview_calls == 0
    assert pose.calls
    assert camera.closed and pose.closed


def test_live_loop_returns_fault_without_starting_pose_or_preview() -> None:
    camera = FakeCamera([], fault="camera unavailable")
    pose_calls = 0
    preview_calls = 0

    def pose_factory(_path: str) -> FakePose:
        nonlocal pose_calls
        pose_calls += 1
        return FakePose()

    def preview_factory() -> FakePreview:
        nonlocal preview_calls
        preview_calls += 1
        return FakePreview()

    code = run_live(
        args(),
        camera_factory=lambda _index: camera,
        pose_factory=pose_factory,
        preview_factory=preview_factory,
        clock=lambda: 0.0,
    )

    assert code == 1
    assert pose_calls == 0
    assert preview_calls == 0
    assert camera.closed


def test_rolling_fps_becomes_nonzero_and_uses_bounded_timestamps() -> None:
    fps = RollingFps()

    assert fps.update(1.0) == 0.0
    assert fps.update(1.1) == pytest.approx(10.0)
    for index in range(2, 50):
        value = fps.update(1.0 + index * 0.1)

    assert value > 9.9
    assert fps.sample_count == 30


def test_live_keys_toggle_overlays_and_reach_application(tmp_path: Path) -> None:
    frames = [object(), object(), object(), object()]
    camera = FakeCamera(frames)
    pose = FakePose()
    preview = FakePreview([ord("l"), ord("d"), ord("c"), ord("q")])
    commands: list[tuple[int, float]] = []

    class FakeApp:
        snapshot = object()

        def process(self, _pose: object, _now: float) -> OutputState:
            return OutputState(
                DiagnosticColor.OFF,
                DiagnosticColor.OFF,
                DiagnosticColor.OFF,
                MonitoringState.HEALTHY,
            )

        def handle_command(self, key: int, now: float) -> bool:
            commands.append((key, now))
            return True

    runtime_args = args()
    runtime_args.calibration_file = str(tmp_path / "calibration.json")
    times = iter((1.0, 1.1, 1.2, 1.3))

    code = run_live(
        runtime_args,
        camera_factory=lambda _index: camera,
        pose_factory=lambda _path: pose,
        preview_factory=lambda: preview,
        app_factory=lambda _calibration: FakeApp(),
        clock=lambda: next(times),
    )

    assert code == 0
    assert [call["show_landmarks"] for call in preview.calls] == [
        True,
        False,
        False,
        False,
    ]
    assert [call["show_details"] for call in preview.calls] == [
        True,
        True,
        False,
        False,
    ]
    assert preview.calls[-1]["fps"] > 0.0
    assert commands == [(ord("c"), 1.2)]
    assert camera.closed and pose.closed and preview.closed


def test_pi_output_receives_snapshot_and_closes(tmp_path: Path) -> None:
    camera = FakeCamera([object()])
    pose = FakePose()
    preview = FakePreview()

    class FakeOutput:
        applied: list[tuple[object, float]] = []
        closed = False

        def apply(self, snapshot: object, now: float) -> None:
            self.applied.append((snapshot, now))

        def close(self) -> None:
            self.closed = True

    output = FakeOutput()
    runtime_args = args()
    runtime_args.pi_leds = True
    runtime_args.calibration_file = str(tmp_path / "calibration.json")

    code = run_live(
        runtime_args,
        camera_factory=lambda _index: camera,
        pose_factory=lambda _path: pose,
        preview_factory=lambda: preview,
        output_factory=lambda: output,
        clock=lambda: 2.0,
    )

    assert code == 0
    assert len(output.applied) == 1
    assert output.applied[0][1] == 2.0
    assert output.closed
