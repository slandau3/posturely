"""Deterministic demo timeline driven through the real posture engine path."""

from __future__ import annotations

import io
import re

from posturely.adapters.demo_pose import demo_frame
from posturely.app import PostureApplication
from posturely.core.types import PoseFrame

_TRANSITION = re.compile(r"^(head|shoulders|torso|monitoring): [a-z]+ -> [a-z]+$")
_DEMO_SECONDS = 70.0
_STEP = 0.25


def _run_demo(out: io.StringIO, seconds: float = _DEMO_SECONDS) -> None:
    app = PostureApplication(out=out)
    now = 0.0
    while now <= seconds:
        app.process(demo_frame(now), now)
        now += _STEP


def _lines(out: io.StringIO) -> list[str]:
    return [line for line in out.getvalue().splitlines() if line.strip()]


def test_demo_timeline_is_deterministic() -> None:
    first = demo_frame(10.0)
    second = demo_frame(10.0)

    assert isinstance(first, PoseFrame)
    assert first == second


def test_demo_timeline_includes_an_absence_window() -> None:
    now = 0.0
    absent: list[float] = []
    while now <= _DEMO_SECONDS:
        if demo_frame(now) is None:
            absent.append(now)
        now += _STEP

    assert absent, "demo script must include a pose-absence segment"


def test_demo_drives_the_full_transition_sequence() -> None:
    out = io.StringIO()
    _run_demo(out)

    expected = [
        "head: off -> amber",
        "head: amber -> red",
        "head: red -> off",
        "shoulders: off -> amber",
        "shoulders: amber -> red",
        "shoulders: red -> off",
        "torso: off -> amber",
        "torso: amber -> red",
        "torso: red -> off",
        "monitoring: healthy -> waiting",
        "monitoring: waiting -> healthy",
    ]
    lines = _lines(out)
    position = 0
    for line in lines:
        if position < len(expected) and line == expected[position]:
            position += 1

    assert position == len(expected), (
        f"missing transition {expected[position]!r} in output {lines}"
    )


def test_headless_output_contains_only_named_transitions() -> None:
    out = io.StringIO()
    _run_demo(out)

    lines = _lines(out)
    assert lines, "demo must report state transitions"
    for line in lines:
        assert _TRANSITION.match(line), f"unexpected output line: {line!r}"
