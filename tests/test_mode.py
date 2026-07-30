from __future__ import annotations

from posturely.core.mode import DeskMode, ModeEstimator
from posturely.core.types import Landmark, PoseFrame


def pose(*, body_midpoint_y: float, reliable: bool = True) -> PoseFrame:
    visibility = 1.0 if reliable else 0.1
    return PoseFrame(
        landmarks={
            "left_shoulder": Landmark(0.4, body_midpoint_y - 0.15, visibility=visibility),
            "right_shoulder": Landmark(0.6, body_midpoint_y - 0.15, visibility=visibility),
            "left_hip": Landmark(0.43, body_midpoint_y + 0.15, visibility=visibility),
            "right_hip": Landmark(0.57, body_midpoint_y + 0.15, visibility=visibility),
        },
        captured_at=0.0,
    )


def test_mode_stays_generic_until_four_of_five_votes_agree() -> None:
    estimator = ModeEstimator()

    for _ in range(4):
        assert estimator.update(pose(body_midpoint_y=0.35)) is DeskMode.GENERIC

    assert estimator.update(pose(body_midpoint_y=0.35)) is DeskMode.STANDING


def test_lower_body_position_stabilizes_as_seated() -> None:
    estimator = ModeEstimator()

    for _ in range(5):
        mode = estimator.update(pose(body_midpoint_y=0.60))

    assert mode is DeskMode.SEATED


def test_mixed_votes_remain_generic() -> None:
    estimator = ModeEstimator()

    frames = [
        pose(body_midpoint_y=0.35),
        pose(body_midpoint_y=0.60),
        pose(body_midpoint_y=0.35),
        pose(body_midpoint_y=0.60),
        pose(body_midpoint_y=0.35),
    ]

    assert [estimator.update(frame) for frame in frames][-1] is DeskMode.GENERIC


def test_absent_and_unreliable_frames_do_not_invent_a_mode() -> None:
    estimator = ModeEstimator()

    for frame in (None, pose(body_midpoint_y=0.60, reliable=False)) * 3:
        assert estimator.update(frame) is DeskMode.GENERIC


def test_explicit_override_wins_and_can_be_cleared() -> None:
    estimator = ModeEstimator()
    for _ in range(5):
        estimator.update(pose(body_midpoint_y=0.35))
    assert estimator.update(pose(body_midpoint_y=0.35)) is DeskMode.STANDING

    estimator.override(DeskMode.SEATED)
    assert estimator.update(pose(body_midpoint_y=0.35)) is DeskMode.SEATED

    estimator.override(None)
    assert estimator.update(pose(body_midpoint_y=0.35)) is DeskMode.STANDING
