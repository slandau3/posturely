"""Command-line entry point for Posturely."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
