from __future__ import annotations

import pytest

from posturely.core.evaluator import PostureEvaluator
from posturely.core.types import (
    HeadFeatures,
    PostureFeatures,
    ShoulderFeatures,
    TorsoFeatures,
)


@pytest.fixture
def neutral_features() -> PostureFeatures:
    return PostureFeatures(
        head=HeadFeatures(horizontal_offset=0.02, neck_angle_degrees=2.0),
        shoulders=ShoulderFeatures(
            line_angle_degrees=1.0,
            asymmetry=0.02,
            elbow_inset=-0.1,
            width_to_torso=0.63,
        ),
        torso=TorsoFeatures(lean_degrees=2.0, compression=1.6),
    )


def test_neutral_geometry_is_confident_and_not_problematic(
    neutral_features: PostureFeatures,
) -> None:
    """An evaluator that treats ordinary neutral variation as bad would create alert fatigue."""
    result = PostureEvaluator().evaluate(neutral_features)

    assert result.head.confident and not result.head.problematic
    assert result.shoulders.confident and not result.shoulders.problematic
    assert result.torso.confident and not result.torso.problematic


@pytest.mark.parametrize(
    ("features", "category"),
    [
        (
            PostureFeatures(
                head=HeadFeatures(horizontal_offset=0.38, neck_angle_degrees=22.0),
                shoulders=ShoulderFeatures(1.0, 0.02, -0.1, 0.63),
                torso=TorsoFeatures(2.0, 1.6),
            ),
            "head",
        ),
        (
            PostureFeatures(
                head=HeadFeatures(0.02, 2.0),
                shoulders=ShoulderFeatures(11.0, 0.18, 0.35, 0.63),
                torso=TorsoFeatures(2.0, 1.6),
            ),
            "shoulders",
        ),
        (
            PostureFeatures(
                head=HeadFeatures(0.02, 2.0),
                shoulders=ShoulderFeatures(1.0, 0.02, -0.1, 0.63),
                torso=TorsoFeatures(17.0, 1.1),
            ),
            "torso",
        ),
    ],
)
def test_each_category_can_trigger_independently(
    features: PostureFeatures,
    category: str,
) -> None:
    """Coupling issue categories would light the wrong virtual dot."""
    result = PostureEvaluator().evaluate(features)

    states = {
        "head": result.head.problematic,
        "shoulders": result.shoulders.problematic,
        "torso": result.torso.problematic,
    }
    assert states == {
        "head": category == "head",
        "shoulders": category == "shoulders",
        "torso": category == "torso",
    }


def test_missing_head_evidence_does_not_suppress_other_categories(
    neutral_features: PostureFeatures,
) -> None:
    """A hidden ear must silence only the head light."""
    features = PostureFeatures(
        head=None,
        shoulders=neutral_features.shoulders,
        torso=TorsoFeatures(lean_degrees=18.0, compression=1.0),
    )

    result = PostureEvaluator().evaluate(features)

    assert not result.head.confident
    assert result.shoulders.confident
    assert result.torso.confident and result.torso.problematic


def test_extreme_head_turn_is_uncertain_instead_of_bad_posture(
    neutral_features: PostureFeatures,
) -> None:
    """A deliberate sideways look must not accumulate toward a head alert."""
    features = PostureFeatures(
        head=HeadFeatures(horizontal_offset=0.9, neck_angle_degrees=58.0),
        shoulders=neutral_features.shoulders,
        torso=neutral_features.torso,
    )

    evidence = PostureEvaluator().evaluate(features).head

    assert not evidence.confident
    assert not evidence.problematic
    assert evidence.reason == "discontinuous head geometry"
