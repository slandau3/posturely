from __future__ import annotations

import argparse
from collections.abc import Callable

from posturely.adapters.demo_pose import demo_frame
from posturely.live import run_live


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
    def __init__(self, key: int = ord("q")) -> None:
        self.key = key
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def __enter__(self) -> FakePreview:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def render(self, **kwargs: object) -> int:
        self.calls.append(kwargs)
        return self.key


def args(*, mirror: bool = True, no_preview: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        camera=0,
        model="/tmp/fake.task",
        mirror=mirror,
        no_preview=no_preview,
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
