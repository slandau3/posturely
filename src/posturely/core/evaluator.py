"""Conservative rules for observable posture geometry."""

from __future__ import annotations

from dataclasses import dataclass

from posturely.core.calibration import Baseline
from posturely.core.types import Evidence, PostureEvidence, PostureFeatures


@dataclass(frozen=True, slots=True)
class GenericThresholds:
    head_offset: float = 0.30
    neck_angle_degrees: float = 18.0
    shoulder_line_degrees: float = 8.0
    shoulder_asymmetry: float = 0.14
    elbow_inset: float = 0.20
    torso_lean_degrees: float = 12.0
    torso_compression: float = 1.25


@dataclass(frozen=True, slots=True)
class CalibrationDeltas:
    head_offset: float = 0.20
    neck_angle_degrees: float = 12.0
    shoulder_line_degrees: float = 6.0
    shoulder_asymmetry: float = 0.10
    elbow_inset: float = 0.15
    width_to_torso: float = 0.12
    torso_lean_degrees: float = 8.0
    torso_compression: float = 0.25


class PostureEvaluator:
    """Convert geometric proxies into independent, confidence-gated evidence."""

    def __init__(
        self,
        thresholds: GenericThresholds | None = None,
        calibration_deltas: CalibrationDeltas | None = None,
    ) -> None:
        self.thresholds = thresholds or GenericThresholds()
        self.calibration_deltas = calibration_deltas or CalibrationDeltas()

    def evaluate(
        self,
        features: PostureFeatures,
        baseline: Baseline | None = None,
    ) -> PostureEvidence:
        return PostureEvidence(
            head=self._head(features, baseline),
            shoulders=self._shoulders(features, baseline),
            torso=self._torso(features, baseline),
        )

    def _head(
        self,
        features: PostureFeatures,
        baseline: Baseline | None,
    ) -> Evidence:
        head = features.head
        if head is None:
            return _uncertain("head landmarks unavailable")
        if abs(head.horizontal_offset) > 0.75 or abs(head.neck_angle_degrees) > 50.0:
            return _uncertain("discontinuous head geometry")
        if baseline is None:
            offset_ratio = abs(head.horizontal_offset) / self.thresholds.head_offset
            angle_ratio = abs(head.neck_angle_degrees) / self.thresholds.neck_angle_degrees
        else:
            offset_ratio = abs(
                head.horizontal_offset
                - _baseline_value(baseline, "head.horizontal_offset", 0.0)
            ) / self.calibration_deltas.head_offset
            angle_ratio = abs(
                head.neck_angle_degrees
                - _baseline_value(baseline, "head.neck_angle_degrees", 0.0)
            ) / self.calibration_deltas.neck_angle_degrees
        magnitude = max(offset_ratio, angle_ratio)
        return _observed(magnitude, "forward head proxy" if magnitude >= 1.0 else "acceptable")

    def _shoulders(
        self,
        features: PostureFeatures,
        baseline: Baseline | None,
    ) -> Evidence:
        shoulders = features.shoulders
        if shoulders is None:
            return _uncertain("shoulder landmarks unavailable")
        if abs(shoulders.line_angle_degrees) > 35.0 or abs(shoulders.elbow_inset) > 1.2:
            return _uncertain("discontinuous shoulder geometry")
        if baseline is None:
            ratios = (
                abs(shoulders.line_angle_degrees)
                / self.thresholds.shoulder_line_degrees,
                shoulders.asymmetry / self.thresholds.shoulder_asymmetry,
                shoulders.elbow_inset / self.thresholds.elbow_inset,
            )
        else:
            ratios = (
                abs(
                    shoulders.line_angle_degrees
                    - _baseline_value(
                        baseline,
                        "shoulders.line_angle_degrees",
                        shoulders.line_angle_degrees,
                    )
                )
                / self.calibration_deltas.shoulder_line_degrees,
                max(
                    0.0,
                    shoulders.asymmetry
                    - _baseline_value(
                        baseline,
                        "shoulders.asymmetry",
                        shoulders.asymmetry,
                    ),
                )
                / self.calibration_deltas.shoulder_asymmetry,
                max(
                    0.0,
                    shoulders.elbow_inset
                    - _baseline_value(
                        baseline,
                        "shoulders.elbow_inset",
                        shoulders.elbow_inset,
                    ),
                )
                / self.calibration_deltas.elbow_inset,
                _width_ratio(shoulders.width_to_torso, baseline, self.calibration_deltas),
            )
        magnitude = max(ratios)
        return _observed(
            magnitude,
            "shoulder imbalance or rounding proxy" if magnitude >= 1.0 else "acceptable",
        )

    def _torso(
        self,
        features: PostureFeatures,
        baseline: Baseline | None,
    ) -> Evidence:
        torso = features.torso
        if torso is None:
            return _uncertain("hip landmarks unavailable")
        if abs(torso.lean_degrees) > 45.0 or torso.compression <= 0.0:
            return _uncertain("discontinuous torso geometry")
        if baseline is None:
            lean_ratio = abs(torso.lean_degrees) / self.thresholds.torso_lean_degrees
            compression_ratio = (
                self.thresholds.torso_compression / torso.compression
                if torso.compression < self.thresholds.torso_compression
                else 0.0
            )
        else:
            lean_ratio = abs(
                torso.lean_degrees
                - _baseline_value(baseline, "torso.lean_degrees", torso.lean_degrees)
            ) / self.calibration_deltas.torso_lean_degrees
            compression_ratio = max(
                0.0,
                _baseline_value(
                    baseline,
                    "torso.compression",
                    torso.compression,
                )
                - torso.compression,
            ) / self.calibration_deltas.torso_compression
        magnitude = max(lean_ratio, compression_ratio)
        return _observed(magnitude, "torso slump proxy" if magnitude >= 1.0 else "acceptable")


def _baseline_value(baseline: Baseline, key: str, fallback: float) -> float:
    return baseline.features.get(key, fallback)


def _width_ratio(
    current: float | None,
    baseline: Baseline,
    deltas: CalibrationDeltas,
) -> float:
    stored = baseline.features.get("shoulders.width_to_torso")
    if current is None or stored is None:
        return 0.0
    return max(0.0, stored - current) / deltas.width_to_torso


def _observed(magnitude: float, reason: str) -> Evidence:
    return Evidence(
        problematic=magnitude >= 1.0,
        confident=True,
        magnitude=magnitude,
        reason=reason,
    )


def _uncertain(reason: str) -> Evidence:
    return Evidence(problematic=False, confident=False, magnitude=0.0, reason=reason)
