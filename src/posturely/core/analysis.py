"""Immutable diagnostic data exposed to presentation and hardware adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from posturely.core.mode import DeskMode
from posturely.core.types import (
    OutputState,
    PostureEvidence,
    PostureFeatures,
)


@dataclass(frozen=True, slots=True)
class IssueProgress:
    """Elapsed timing for one diagnostic category."""

    problematic_seconds: float
    corrected_seconds: float
    next_transition_seconds: float | None


@dataclass(frozen=True, slots=True)
class DiagnosticProgress:
    """Independent timing progress for all three posture categories."""

    head: IssueProgress
    shoulders: IssueProgress
    torso: IssueProgress


class CalibrationPhase(StrEnum):
    IDLE = "idle"
    NEEDS_MODE = "needs_mode"
    CAPTURING = "capturing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CONFIRM_CLEAR = "confirm_clear"


@dataclass(frozen=True, slots=True)
class CalibrationStatus:
    phase: CalibrationPhase
    mode: DeskMode | None
    progress: float
    message: str


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    """Everything an output adapter may display for the current frame."""

    state: OutputState
    features: PostureFeatures
    evidence: PostureEvidence
    progress: DiagnosticProgress
    mode: DeskMode
    baseline_mode: DeskMode | None
    calibration: CalibrationStatus
