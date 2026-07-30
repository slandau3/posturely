"""Dependency-injected live monitoring loop."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import ExitStack
from time import monotonic
from typing import Any

from posturely.app import PostureApplication


def run_live(
    args: argparse.Namespace,
    *,
    camera_factory: Callable[[int], Any] | None = None,
    pose_factory: Callable[[str], Any] | None = None,
    preview_factory: Callable[[], Any] | None = None,
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

    app = PostureApplication()
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
            timestamp_ms = int(now * 1000)
            pose = pose_adapter.detect(frame, timestamp_ms)
            state = app.process(pose, now)
            if preview is not None:
                key = preview.render(
                    frame=frame,
                    pose=pose,
                    state=state,
                    fps=0.0,
                    mirror=args.mirror,
                )
                if key in (ord("q"), ord("Q"), 27):
                    return 0
