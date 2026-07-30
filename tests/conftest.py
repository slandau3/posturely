from __future__ import annotations

import pytest

from posturely.core.types import Landmark, PoseFrame


@pytest.fixture
def neutral_pose() -> PoseFrame:
    return PoseFrame(
        landmarks={
            "nose": Landmark(0.50, 0.18),
            "left_ear": Landmark(0.45, 0.20),
            "right_ear": Landmark(0.55, 0.20),
            "left_shoulder": Landmark(0.40, 0.36),
            "right_shoulder": Landmark(0.60, 0.36),
            "left_elbow": Landmark(0.38, 0.55),
            "right_elbow": Landmark(0.62, 0.55),
            "left_hip": Landmark(0.44, 0.68),
            "right_hip": Landmark(0.56, 0.68),
        },
        captured_at=1.0,
    )
