"""Platform-neutral boundary for posture feedback devices."""

from __future__ import annotations

from typing import Protocol

from posturely.core.analysis import AnalysisSnapshot


class PostureOutput(Protocol):
    def apply(self, snapshot: AnalysisSnapshot, now: float) -> None:
        """Apply the latest posture state to an output device."""

    def close(self) -> None:
        """Turn outputs off and release hardware resources."""
