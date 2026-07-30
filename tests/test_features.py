from __future__ import annotations

from dataclasses import FrozenInstanceError
from math import isclose

import pytest

from posturely.core.features import extract_features
from posturely.core.types import (
    DiagnosticColor,
    Landmark,
    MonitoringState,
    OutputState,
    PoseFrame,
)


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("x", {"x": -0.01, "y": 0.5}),
        ("y", {"x": 0.5, "y": 1.01}),
        ("visibility", {"x": 0.5, "y": 0.5, "visibility": 1.1}),
        ("presence", {"x": 0.5, "y": 0.5, "presence": -0.1}),
    ],
)
def test_landmark_rejects_values_outside_normalized_range(
    field: str, kwargs: dict[str, float]
) -> None:
    """Removing coordinate validation would admit invalid pose geometry."""
    with pytest.raises(ValueError, match=field):
        Landmark(**kwargs)


def test_landmark_is_immutable() -> None:
    """Making landmarks mutable would let adapters corrupt an evaluated frame."""
    landmark = Landmark(0.5, 0.5)

    with pytest.raises(FrozenInstanceError):
        landmark.x = 0.6  # type: ignore[misc]


def test_pose_reliability_requires_visibility_presence_and_existence() -> None:
    """Ignoring either confidence channel would turn uncertain landmarks into evidence."""
    frame = PoseFrame(
        landmarks={
            "good": Landmark(0.5, 0.5, visibility=0.8, presence=0.9),
            "hidden": Landmark(0.5, 0.5, visibility=0.4, presence=0.9),
            "absent": Landmark(0.5, 0.5, visibility=0.9, presence=0.4),
        },
        captured_at=3.0,
    )

    assert frame.reliable("good", minimum=0.55)
    assert not frame.reliable("hidden", minimum=0.55)
    assert not frame.reliable("absent", minimum=0.55)
    assert not frame.reliable("missing", minimum=0.55)


def test_output_state_keeps_three_independent_diagnostics() -> None:
    """Collapsing diagnostics would prevent issue-specific lights."""
    output = OutputState(
        head=DiagnosticColor.RED,
        shoulders=DiagnosticColor.AMBER,
        torso=DiagnosticColor.OFF,
        monitoring=MonitoringState.HEALTHY,
    )

    assert (output.head, output.shoulders, output.torso) == (
        DiagnosticColor.RED,
        DiagnosticColor.AMBER,
        DiagnosticColor.OFF,
    )


def test_neutral_pose_produces_hand_checked_geometry(neutral_pose: PoseFrame) -> None:
    """Swapping axes or normalization would corrupt the evaluator's physical meaning."""
    features = extract_features(neutral_pose)

    assert features.head is not None
    assert isclose(features.head.horizontal_offset, 0.0, abs_tol=1e-9)
    assert isclose(features.head.neck_angle_degrees, 0.0, abs_tol=1e-9)

    assert features.shoulders is not None
    assert isclose(features.shoulders.line_angle_degrees, 0.0, abs_tol=1e-9)
    assert isclose(features.shoulders.asymmetry, 0.0, abs_tol=1e-9)
    assert isclose(features.shoulders.elbow_inset, -0.2, abs_tol=1e-9)

    assert features.torso is not None
    assert isclose(features.torso.lean_degrees, 0.0, abs_tol=1e-9)
    assert isclose(features.torso.compression, 1.6, abs_tol=1e-9)


def test_features_are_invariant_to_translation_and_uniform_scale(
    neutral_pose: PoseFrame,
) -> None:
    """Using pixel position or body size would break sit/stand and camera-distance portability."""
    transformed = PoseFrame(
        landmarks={
            name: Landmark(
                x=0.1 + point.x * 0.7,
                y=0.08 + point.y * 0.7,
                z=point.z * 0.7,
                visibility=point.visibility,
                presence=point.presence,
            )
            for name, point in neutral_pose.landmarks.items()
        },
        captured_at=neutral_pose.captured_at,
    )

    transformed_features = extract_features(transformed)
    original_features = extract_features(neutral_pose)

    assert transformed_features.head is not None
    assert original_features.head is not None
    assert transformed_features.head.horizontal_offset == pytest.approx(
        original_features.head.horizontal_offset
    )
    assert transformed_features.head.neck_angle_degrees == pytest.approx(
        original_features.head.neck_angle_degrees
    )
    assert transformed_features.shoulders is not None
    assert original_features.shoulders is not None
    assert transformed_features.shoulders.elbow_inset == pytest.approx(
        original_features.shoulders.elbow_inset
    )
    assert transformed_features.shoulders.width_to_torso == pytest.approx(
        original_features.shoulders.width_to_torso
    )
    assert transformed_features.torso is not None
    assert original_features.torso is not None
    assert transformed_features.torso.compression == pytest.approx(
        original_features.torso.compression
    )


def test_unreliable_hips_only_suppress_torso_features(neutral_pose: PoseFrame) -> None:
    """One low-confidence metric must not silence unrelated diagnostic lights."""
    landmarks = dict(neutral_pose.landmarks)
    landmarks["left_hip"] = Landmark(0.44, 0.68, visibility=0.2)
    frame = PoseFrame(landmarks=landmarks, captured_at=2.0)

    features = extract_features(frame)

    assert features.head is not None
    assert features.shoulders is not None
    assert features.torso is None
