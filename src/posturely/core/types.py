"""Small, platform-neutral data contracts used by the posture engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: float = 1.0

    def __post_init__(self) -> None:
        for field_name in ("x", "y", "visibility", "presence"):
            value = getattr(self, field_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1, got {value}")


@dataclass(frozen=True, slots=True)
class PoseFrame:
    landmarks: Mapping[str, Landmark]
    captured_at: float

    def reliable(self, name: str, minimum: float = 0.55) -> bool:
        landmark = self.landmarks.get(name)
        return bool(
            landmark
            and landmark.visibility >= minimum
            and landmark.presence >= minimum
        )


@dataclass(frozen=True, slots=True)
class HeadFeatures:
    horizontal_offset: float
    neck_angle_degrees: float


@dataclass(frozen=True, slots=True)
class ShoulderFeatures:
    line_angle_degrees: float
    asymmetry: float
    elbow_inset: float
    width_to_torso: float | None


@dataclass(frozen=True, slots=True)
class TorsoFeatures:
    lean_degrees: float
    compression: float


@dataclass(frozen=True, slots=True)
class PostureFeatures:
    head: HeadFeatures | None
    shoulders: ShoulderFeatures | None
    torso: TorsoFeatures | None


class DiagnosticColor(str, Enum):
    OFF = "off"
    AMBER = "amber"
    RED = "red"


class MonitoringState(str, Enum):
    HEALTHY = "healthy"
    WAITING = "waiting"
    FAULT = "fault"


@dataclass(frozen=True, slots=True)
class OutputState:
    head: DiagnosticColor
    shoulders: DiagnosticColor
    torso: DiagnosticColor
    monitoring: MonitoringState
