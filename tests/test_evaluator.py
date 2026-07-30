from __future__ import annotations

import pytest

from posturely.core.calibration import Baseline, CalibrationMode
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


def calibrated_baseline() -> Baseline:
    return Baseline(
        mode=CalibrationMode.SEATED,
        features={
            "head.horizontal_offset": 0.20,
            "head.neck_angle_degrees": 10.0,
            "shoulders.line_angle_degrees": 3.0,
            "shoulders.asymmetry": 0.05,
            "shoulders.elbow_inset": 0.05,
            "shoulders.width_to_torso": 0.70,
            "torso.lean_degrees": 5.0,
            "torso.compression": 1.60,
        },
        captured_at=1.0,
    )


def calibrated_features(**changes: float | None) -> PostureFeatures:
    values: dict[str, float | None] = {
        "head_offset": 0.20,
        "neck_angle": 10.0,
        "line_angle": 3.0,
        "asymmetry": 0.05,
        "elbow_inset": 0.05,
        "width_to_torso": 0.70,
        "lean": 5.0,
        "compression": 1.60,
    }
    values.update(changes)
    return PostureFeatures(
        head=HeadFeatures(
            horizontal_offset=float(values["head_offset"]),
            neck_angle_degrees=float(values["neck_angle"]),
        ),
        shoulders=ShoulderFeatures(
            line_angle_degrees=float(values["line_angle"]),
            asymmetry=float(values["asymmetry"]),
            elbow_inset=float(values["elbow_inset"]),
            width_to_torso=values["width_to_torso"],
        ),
        torso=TorsoFeatures(
            lean_degrees=float(values["lean"]),
            compression=float(values["compression"]),
        ),
    )


def test_calibrated_baseline_itself_is_acceptable() -> None:
    result = PostureEvaluator().evaluate(
        calibrated_features(),
        baseline=calibrated_baseline(),
    )

    assert not result.head.problematic
    assert not result.shoulders.problematic
    assert not result.torso.problematic
    assert result.head.magnitude == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("changes", "category"),
    [
        ({"head_offset": 0.41}, "head"),
        ({"line_angle": 9.1}, "shoulders"),
        ({"compression": 1.34}, "torso"),
    ],
)
def test_calibrated_deltas_trigger_only_their_category(
    changes: dict[str, float],
    category: str,
) -> None:
    result = PostureEvaluator().evaluate(
        calibrated_features(**changes),
        baseline=calibrated_baseline(),
    )

    assert {
        "head": result.head.problematic,
        "shoulders": result.shoulders.problematic,
        "torso": result.torso.problematic,
    } == {
        "head": category == "head",
        "shoulders": category == "shoulders",
        "torso": category == "torso",
    }


def test_calibrated_shoulders_allow_missing_optional_width_ratio() -> None:
    result = PostureEvaluator().evaluate(
        calibrated_features(width_to_torso=None),
        baseline=calibrated_baseline(),
    )

    assert result.shoulders.confident
    assert not result.shoulders.problematic


def test_explicit_no_baseline_exactly_matches_generic_evaluation(
    neutral_features: PostureFeatures,
) -> None:
    evaluator = PostureEvaluator()

    assert evaluator.evaluate(neutral_features, baseline=None) == evaluator.evaluate(
        neutral_features
    )
