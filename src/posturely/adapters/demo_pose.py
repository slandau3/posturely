"""Deterministic synthetic pose timeline for headless demo runs.

Pure functions only: no camera stack, no cv2, no mediapipe. The 70-second
script walks each diagnostic category through amber and red, then back to
off, and finishes with a pose-absence window.
"""

from __future__ import annotations

from posturely.core.types import Landmark, PoseFrame

# Script boundaries in seconds, chosen so the state machine's 5s amber,
# 15s red, and 2s recovery thresholds each fire inside their segment.
_HEAD_BAD = (5.0, 23.0)
_SHOULDERS_BAD = (25.0, 43.0)
_TORSO_BAD = (45.0, 63.0)
_ABSENT = (65.0, 68.0)


def _base_landmarks() -> dict[str, Landmark]:
    """Neutral seated pose: every category well inside acceptable limits."""
    return {
        "left_shoulder": Landmark(0.40, 0.40),
        "right_shoulder": Landmark(0.60, 0.40),
        "left_ear": Landmark(0.48, 0.20),
        "right_ear": Landmark(0.52, 0.20),
        "left_elbow": Landmark(0.41, 0.55),
        "right_elbow": Landmark(0.59, 0.55),
        "left_hip": Landmark(0.42, 0.70),
        "right_hip": Landmark(0.58, 0.70),
    }


def demo_frame(now: float) -> PoseFrame | None:
    """Return the scripted pose at ``now`` seconds, or None while absent."""
    if _ABSENT[0] <= now < _ABSENT[1]:
        return None
    landmarks = _base_landmarks()
    if _HEAD_BAD[0] <= now < _HEAD_BAD[1]:
        # Ears pushed forward: horizontal offset 0.45 vs 0.30 threshold.
        landmarks["left_ear"] = Landmark(0.57, 0.20)
        landmarks["right_ear"] = Landmark(0.61, 0.20)
    elif _SHOULDERS_BAD[0] <= now < _SHOULDERS_BAD[1]:
        # Dropped right shoulder: line ~16.7 degrees vs 8.0 threshold.
        landmarks["right_shoulder"] = Landmark(0.60, 0.46)
    elif _TORSO_BAD[0] <= now < _TORSO_BAD[1]:
        # Upper body shifted forward 0.08: lean ~14.9 degrees vs 12.0 threshold.
        for name in (
            "left_shoulder",
            "right_shoulder",
            "left_ear",
            "right_ear",
            "left_elbow",
            "right_elbow",
        ):
            base = landmarks[name]
            landmarks[name] = Landmark(base.x + 0.08, base.y)
    return PoseFrame(landmarks=landmarks, captured_at=now)
