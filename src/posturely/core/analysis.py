"""Immutable diagnostic data exposed to presentation and hardware adapters."""

from __future__ import annotations

from dataclasses import dataclass


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
