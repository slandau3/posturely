from __future__ import annotations

import io
import sys

from posturely.__main__ import build_parser, main


class FakeClock:
    """Manual monotonic clock; doubling as the injected sleep keeps tests real-time free."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_parser_exposes_runtime_modes() -> None:
    """Removing a supported runtime mode must break the public CLI contract."""
    help_text = build_parser().format_help()

    for flag in (
        "--demo",
        "--camera",
        "--model",
        "--mirror",
        "--no-preview",
        "--demo-seconds",
    ):
        assert flag in help_text


def test_headless_demo_runs_full_script_without_native_libraries() -> None:
    """`--demo --no-preview` must run deterministically with no camera stack or sleeping."""
    clock = FakeClock()
    out = io.StringIO()

    exit_code = main(
        ["--demo", "--no-preview", "--demo-seconds", "70"],
        clock=clock,
        sleep=clock.advance,
        out=out,
    )

    assert exit_code == 0
    text = out.getvalue()
    for line in (
        "head: off -> amber",
        "head: amber -> red",
        "shoulders: off -> amber",
        "shoulders: amber -> red",
        "torso: off -> amber",
        "torso: amber -> red",
        "monitoring: healthy -> waiting",
        "monitoring: waiting -> healthy",
    ):
        assert line in text
    assert "cv2" not in sys.modules
    assert "mediapipe" not in sys.modules
