"""Extract scale-normalized geometric proxies from pose landmarks."""

from __future__ import annotations

from math import atan2, degrees, hypot

from posturely.core.types import (
    HeadFeatures,
    Landmark,
    PoseFrame,
    PostureFeatures,
    ShoulderFeatures,
    TorsoFeatures,
)

_CONFIDENCE_MINIMUM = 0.55
_MINIMUM_SCALE = 1e-6


def _midpoint(left: Landmark, right: Landmark) -> tuple[float, float]:
    return ((left.x + right.x) / 2.0, (left.y + right.y) / 2.0)


def _distance(left: Landmark, right: Landmark) -> float:
    return hypot(right.x - left.x, right.y - left.y)


def _angle_from_vertical(dx: float, dy: float) -> float:
    return degrees(atan2(dx, abs(dy)))


def _all_reliable(frame: PoseFrame, *names: str) -> bool:
    return all(frame.reliable(name, _CONFIDENCE_MINIMUM) for name in names)


def extract_features(frame: PoseFrame) -> PostureFeatures:
    shoulder_names = ("left_shoulder", "right_shoulder")
    if not _all_reliable(frame, *shoulder_names):
        return PostureFeatures(head=None, shoulders=None, torso=None)

    left_shoulder = frame.landmarks["left_shoulder"]
    right_shoulder = frame.landmarks["right_shoulder"]
    shoulder_midpoint = _midpoint(left_shoulder, right_shoulder)
    shoulder_width = _distance(left_shoulder, right_shoulder)
    if shoulder_width <= _MINIMUM_SCALE:
        return PostureFeatures(head=None, shoulders=None, torso=None)

    head = _head_features(frame, shoulder_midpoint, shoulder_width)
    shoulders = _shoulder_features(frame, shoulder_width)
    torso = _torso_features(frame, shoulder_midpoint, shoulder_width)
    return PostureFeatures(head=head, shoulders=shoulders, torso=torso)


def _head_features(
    frame: PoseFrame,
    shoulder_midpoint: tuple[float, float],
    shoulder_width: float,
) -> HeadFeatures | None:
    if not _all_reliable(frame, "left_ear", "right_ear"):
        return None
    ear_midpoint = _midpoint(frame.landmarks["left_ear"], frame.landmarks["right_ear"])
    dx = ear_midpoint[0] - shoulder_midpoint[0]
    dy = ear_midpoint[1] - shoulder_midpoint[1]
    return HeadFeatures(
        horizontal_offset=dx / shoulder_width,
        neck_angle_degrees=_angle_from_vertical(dx, dy),
    )


def _shoulder_features(
    frame: PoseFrame,
    shoulder_width: float,
) -> ShoulderFeatures | None:
    if not _all_reliable(
        frame,
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
    ):
        return None
    left_shoulder = frame.landmarks["left_shoulder"]
    right_shoulder = frame.landmarks["right_shoulder"]
    left_elbow = frame.landmarks["left_elbow"]
    right_elbow = frame.landmarks["right_elbow"]
    shoulder_dx = right_shoulder.x - left_shoulder.x
    shoulder_dy = right_shoulder.y - left_shoulder.y
    width_to_torso = None
    if _all_reliable(frame, "left_hip", "right_hip"):
        hip_midpoint = _midpoint(frame.landmarks["left_hip"], frame.landmarks["right_hip"])
        shoulder_midpoint = _midpoint(left_shoulder, right_shoulder)
        torso_length = hypot(
            hip_midpoint[0] - shoulder_midpoint[0],
            hip_midpoint[1] - shoulder_midpoint[1],
        )
        if torso_length > _MINIMUM_SCALE:
            width_to_torso = shoulder_width / torso_length
    return ShoulderFeatures(
        line_angle_degrees=degrees(atan2(shoulder_dy, shoulder_dx)),
        asymmetry=abs(shoulder_dy) / shoulder_width,
        elbow_inset=(
            (left_elbow.x - left_shoulder.x)
            + (right_shoulder.x - right_elbow.x)
        )
        / shoulder_width,
        width_to_torso=width_to_torso,
    )


def _torso_features(
    frame: PoseFrame,
    shoulder_midpoint: tuple[float, float],
    shoulder_width: float,
) -> TorsoFeatures | None:
    if not _all_reliable(frame, "left_hip", "right_hip"):
        return None
    hip_midpoint = _midpoint(frame.landmarks["left_hip"], frame.landmarks["right_hip"])
    dx = shoulder_midpoint[0] - hip_midpoint[0]
    dy = shoulder_midpoint[1] - hip_midpoint[1]
    return TorsoFeatures(
        lean_degrees=_angle_from_vertical(dx, dy),
        compression=abs(dy) / shoulder_width,
    )
