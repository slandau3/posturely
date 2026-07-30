"""Command-line entry point for Posturely."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from time import monotonic
from time import sleep as _real_sleep
from typing import TextIO

from posturely.adapters.demo_pose import demo_frame
from posturely.app import PostureApplication

_DEMO_STEP_SECONDS = 0.25


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="posturely",
        description="Private, local posture feedback with quiet virtual lights.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--demo", action="store_true", help="run deterministic synthetic poses")
    source.add_argument("--camera", type=int, default=0, help="camera index for live monitoring")
    parser.add_argument("--model", help="path to a MediaPipe Pose Landmarker model")
    parser.add_argument("--mirror", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--no-preview", action="store_true", help="run without a video window")
    parser.add_argument(
        "--demo-seconds",
        type=float,
        default=70.0,
        help="length of the synthetic demo timeline",
    )
    return parser


def _run_demo(
    seconds: float,
    *,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    out: TextIO,
) -> int:
    """Step the scripted timeline through the application; no native libraries."""
    app = PostureApplication(out=out)
    start = clock()
    while True:
        now = clock() - start
        if now > seconds:
            break
        app.process(demo_frame(now), now)
        sleep(_DEMO_STEP_SECONDS)
    return 0


def main(
    argv: Sequence[str] | None = None,
    *,
    clock: Callable[[], float] = monotonic,
    sleep: Callable[[float], None] = _real_sleep,
    out: TextIO | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    if args.demo:
        return _run_demo(args.demo_seconds, clock=clock, sleep=sleep, out=out or sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
