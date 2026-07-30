"""Automatic, camera-free visual simulation of the Posturely appliance."""

from __future__ import annotations

import sys
from collections.abc import Callable
from time import sleep as _real_sleep
from typing import Any, TextIO

from posturely.adapters.demo_pose import demo_frame
from posturely.app import PostureApplication

_SIMULATION_STEP_SECONDS = 0.25
_QUIT_KEYS = {ord("q"), 27}


def _blank_frame() -> Any:
    """Create a fresh dark canvas while keeping NumPy an optional lazy import."""
    import numpy as np

    return np.full((480, 640, 3), 18, dtype=np.uint8)


def run_visual_demo(
    *,
    seconds: float,
    speed: float,
    mirror: bool,
    out: TextIO | None = None,
    preview_factory: Callable[[], Any] | None = None,
    frame_factory: Callable[[], Any] = _blank_frame,
    sleep: Callable[[float], None] = _real_sleep,
) -> int:
    """Render the real posture engine against an accelerated scripted pose."""
    if speed <= 0:
        raise ValueError("demo speed must be positive")
    if preview_factory is None:
        from posturely.adapters.opencv_preview import OpenCVPreview

        preview_factory = OpenCVPreview

    app = PostureApplication(out=out or sys.stdout)
    preview = preview_factory()
    now = 0.0
    try:
        while now <= seconds:
            pose = demo_frame(now)
            state = app.process(pose, now)
            key = preview.render(
                frame=frame_factory(),
                pose=pose,
                state=state,
                fps=speed / _SIMULATION_STEP_SECONDS,
                mirror=mirror,
                status_text=f"AUTOMATIC DEMO - {speed:g}x - no camera",
            )
            if key in _QUIT_KEYS:
                break
            sleep(_SIMULATION_STEP_SECONDS / speed)
            now += _SIMULATION_STEP_SECONDS
    finally:
        preview.close()
    return 0
