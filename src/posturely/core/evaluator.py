"""Conservative rules for observable posture geometry."""

from __future__ import annotations

from dataclasses import dataclass

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


class PostureEvaluator:
    """Convert geometric proxies into independent, confidence-gated evidence."""

    def __init__(self, thresholds: GenericThresholds | None = None) -> None:
        self.thresholds = thresholds or GenericThresholds()

    def evaluate(self, features: PostureFeatures) -> PostureEvidence:
        return PostureEvidence(
            head=self._head(features),
            shoulders=self._shoulders(features),
            torso=self._torso(features),
        )

    def _head(self, features: PostureFeatures) -> Evidence:
        head = features.head
        if head is None:
            return _uncertain("head landmarks unavailable")
        if abs(head.horizontal_offset) > 0.75 or abs(head.neck_angle_degrees) > 50.0:
            return _uncertain("discontinuous head geometry")
        offset_ratio = abs(head.horizontal_offset) / self.thresholds.head_offset
        angle_ratio = abs(head.neck_angle_degrees) / self.thresholds.neck_angle_degrees
        magnitude = max(offset_ratio, angle_ratio)
        return _observed(magnitude, "forward head proxy" if magnitude >= 1.0 else "acceptable")

    def _shoulders(self, features: PostureFeatures) -> Evidence:
        shoulders = features.shoulders
        if shoulders is None:
            return _uncertain("shoulder landmarks unavailable")
        if abs(shoulders.line_angle_degrees) > 35.0 or abs(shoulders.elbow_inset) > 1.2:
            return _uncertain("discontinuous shoulder geometry")
        magnitude = max(
            abs(shoulders.line_angle_degrees) / self.thresholds.shoulder_line_degrees,
            shoulders.asymmetry / self.thresholds.shoulder_asymmetry,
            shoulders.elbow_inset / self.thresholds.elbow_inset,
        )
        return _observed(
            magnitude,
            "shoulder imbalance or rounding proxy" if magnitude >= 1.0 else "acceptable",
        )

    def _torso(self, features: PostureFeatures) -> Evidence:
        torso = features.torso
        if torso is None:
            return _uncertain("hip landmarks unavailable")
        if abs(torso.lean_degrees) > 45.0 or torso.compression <= 0.0:
            return _uncertain("discontinuous torso geometry")
        lean_ratio = abs(torso.lean_degrees) / self.thresholds.torso_lean_degrees
        compression_ratio = (
            self.thresholds.torso_compression / torso.compression
            if torso.compression < self.thresholds.torso_compression
            else 0.0
        )
        magnitude = max(lean_ratio, compression_ratio)
        return _observed(magnitude, "torso slump proxy" if magnitude >= 1.0 else "acceptable")


def _observed(magnitude: float, reason: str) -> Evidence:
    return Evidence(
        problematic=magnitude >= 1.0,
        confident=True,
        magnitude=magnitude,
        reason=reason,
    )


def _uncertain(reason: str) -> Evidence:
    return Evidence(problematic=False, confident=False, magnitude=0.0, reason=reason)
