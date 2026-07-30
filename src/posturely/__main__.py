"""Command-line entry point for Posturely."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
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
        "--calibration-file",
        default=".posturely-calibration.json",
        help="numeric-only local calibration file",
    )
    parser.add_argument(
        "--details",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="show developer scores and countdowns",
    )
    parser.add_argument(
        "--landmarks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="show pose landmarks in the preview",
    )
    parser.add_argument(
        "--pi-leds",
        action="store_true",
        help="drive the Raspberry Pi prototype LEDs",
    )
    parser.add_argument(
        "--demo-seconds",
        type=float,
        default=70.0,
        help="length of the synthetic demo timeline",
    )
    parser.add_argument(
        "--demo-speed",
        type=float,
        default=10.0,
        help="visual demo playback speed (default: 10x)",
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
    live: Callable[[argparse.Namespace], int] | None = None,
    visual_demo: Callable[[argparse.Namespace], int] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo:
        if args.no_preview:
            return _run_demo(
                args.demo_seconds,
                clock=clock,
                sleep=sleep,
                out=out or sys.stdout,
            )
        if visual_demo is not None:
            return visual_demo(args)
        from posturely.demo_ui import run_visual_demo

        return run_visual_demo(
            seconds=args.demo_seconds,
            speed=args.demo_speed,
            mirror=args.mirror,
            out=out or sys.stdout,
        )
    if not args.model:
        parser.error("--model is required for live camera monitoring")
    if not Path(args.model).is_file():
        parser.error(f"model file not found: {args.model}")
    if live is None:
        from posturely.live import run_live

        live = run_live
    return live(args)


if __name__ == "__main__":
    raise SystemExit(main())
