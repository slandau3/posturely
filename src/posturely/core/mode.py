"""Coarse seated/standing estimation for a fixed desk camera view."""

from __future__ import annotations

from collections import Counter, deque
from enum import StrEnum

from posturely.core.types import PoseFrame

_REQUIRED_LANDMARKS = (
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
)


class DeskMode(StrEnum):
    GENERIC = "generic"
    SEATED = "seated"
    STANDING = "standing"


class ModeEstimator:
    """Stabilize a coarse mode using five bounded, screen-relative votes."""

    def __init__(self) -> None:
        self._votes: deque[DeskMode] = deque(maxlen=5)
        self._override: DeskMode | None = None

    def update(self, frame: PoseFrame | None) -> DeskMode:
        vote = _vote(frame)
        if vote is not None:
            self._votes.append(vote)
        if self._override is not None:
            return self._override
        if len(self._votes) < self._votes.maxlen:
            return DeskMode.GENERIC
        mode, count = Counter(self._votes).most_common(1)[0]
        return mode if count >= 4 else DeskMode.GENERIC

    def override(self, mode: DeskMode | None) -> None:
        if mode is DeskMode.GENERIC:
            mode = None
        self._override = mode


def _vote(frame: PoseFrame | None) -> DeskMode | None:
    if frame is None or not all(frame.reliable(name) for name in _REQUIRED_LANDMARKS):
        return None
    body_midpoint_y = sum(
        frame.landmarks[name].y for name in _REQUIRED_LANDMARKS
    ) / len(_REQUIRED_LANDMARKS)
    return DeskMode.STANDING if body_midpoint_y < 0.48 else DeskMode.SEATED
