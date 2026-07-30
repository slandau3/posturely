"""Dependency-injected live monitoring loop."""

from __future__ import annotations

import argparse
from collections import deque
from collections.abc import Callable
from contextlib import ExitStack
from pathlib import Path
from time import monotonic
from typing import Any

from posturely.app import PostureApplication
from posturely.calibration_runtime import CalibrationController


class RollingFps:
    """Measure analyzed FPS over a bounded recent timestamp window."""

    def __init__(self, maximum_samples: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=maximum_samples)

    @property
    def sample_count(self) -> int:
        return len(self._timestamps)

    def update(self, now: float) -> float:
        self._timestamps.append(now)
        if len(self._timestamps) < 2:
            return 0.0
        span = self._timestamps[-1] - self._timestamps[0]
        return (len(self._timestamps) - 1) / span if span > 0.0 else 0.0


def run_live(
    args: argparse.Namespace,
    *,
    camera_factory: Callable[[int], Any] | None = None,
    pose_factory: Callable[[str], Any] | None = None,
    preview_factory: Callable[[], Any] | None = None,
    app_factory: Callable[[CalibrationController], Any] | None = None,
    clock: Callable[[], float] = monotonic,
) -> int:
    """Run until q is pressed or a camera fault ends the stream."""
    if camera_factory is None:
        from posturely.adapters.opencv_camera import OpenCVCamera

        camera_factory = OpenCVCamera
    if pose_factory is None:
        from posturely.adapters.mediapipe_pose import MediaPipePose

        pose_factory = MediaPipePose
    if preview_factory is None:
        from posturely.adapters.opencv_preview import OpenCVPreview

        preview_factory = OpenCVPreview

    calibration = CalibrationController(Path(args.calibration_file))
    app = (
        app_factory(calibration)
        if app_factory is not None
        else PostureApplication(calibration=calibration)
    )
    fps_counter = RollingFps()
    show_landmarks = args.landmarks
    show_details = args.details
    with ExitStack() as stack:
        camera = stack.enter_context(camera_factory(args.camera))
        if camera.fault is not None:
            return 1
        pose_adapter = stack.enter_context(pose_factory(args.model))
        preview = (
            None
            if args.no_preview
            else stack.enter_context(preview_factory())
        )

        while True:
            frame = camera.read()
            if frame is None:
                return 1 if camera.fault is not None else 0
            now = clock()
            fps = fps_counter.update(now)
            timestamp_ms = int(now * 1000)
            pose = pose_adapter.detect(frame, timestamp_ms)
            state = app.process(pose, now)
            if preview is not None:
                key = preview.render(
                    frame=frame,
                    pose=pose,
                    state=state,
                    fps=fps,
                    mirror=args.mirror,
                    snapshot=app.snapshot,
                    show_landmarks=show_landmarks,
                    show_details=show_details,
                )
                if key in (ord("q"), ord("Q"), 27):
                    return 0
                if key in (ord("l"), ord("L")):
                    show_landmarks = not show_landmarks
                elif key in (ord("d"), ord("D")):
                    show_details = not show_details
                else:
                    app.handle_command(key, now)
