"""Optional numeric calibration: median baselines for seated and standing work."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from statistics import median
from time import monotonic

from posturely.core.types import PostureFeatures


class CalibrationMode(str, Enum):
    SEATED = "seated"
    STANDING = "standing"


class CalibrationError(Exception):
    """Raised when a capture or a persisted baseline is unusable."""


@dataclass(frozen=True, slots=True)
class Baseline:
    """Median numeric features captured in one mode; never landmarks or frames."""

    mode: CalibrationMode
    features: dict[str, float]
    captured_at: float


def _flatten(features: PostureFeatures) -> dict[str, float]:
    flat: dict[str, float] = {}
    if features.head is not None:
        flat["head.horizontal_offset"] = features.head.horizontal_offset
        flat["head.neck_angle_degrees"] = features.head.neck_angle_degrees
    if features.shoulders is not None:
        flat["shoulders.line_angle_degrees"] = features.shoulders.line_angle_degrees
        flat["shoulders.asymmetry"] = features.shoulders.asymmetry
        flat["shoulders.elbow_inset"] = features.shoulders.elbow_inset
        if features.shoulders.width_to_torso is not None:
            flat["shoulders.width_to_torso"] = features.shoulders.width_to_torso
    if features.torso is not None:
        flat["torso.lean_degrees"] = features.torso.lean_degrees
        flat["torso.compression"] = features.torso.compression
    return flat


class CalibrationSession:
    """Collect complete, stable feature samples over a fixed capture window."""

    MIN_SAMPLES = 5
    MIN_SPAN_SECONDS = 5.0
    # Largest plausible jitter per feature while the user holds a calibration pose.
    MAX_STABLE_RANGE = {
        "head.horizontal_offset": 0.1,
        "head.neck_angle_degrees": 4.0,
        "shoulders.line_angle_degrees": 4.0,
        "shoulders.asymmetry": 0.1,
        "shoulders.elbow_inset": 0.1,
        "shoulders.width_to_torso": 0.2,
        "torso.lean_degrees": 4.0,
        "torso.compression": 0.3,
    }

    def __init__(self, mode: CalibrationMode, clock: Callable[[], float] = monotonic) -> None:
        self._mode = mode
        self._clock = clock
        self._samples: list[tuple[float, dict[str, float]]] = []

    def add_sample(self, features: PostureFeatures) -> bool:
        """Record one sample; skip (return False) when any feature group is missing."""
        if features.head is None or features.shoulders is None or features.torso is None:
            return False
        self._samples.append((self._clock(), _flatten(features)))
        return True

    def finish(self) -> Baseline:
        """Collapse the capture window into per-feature medians."""
        if len(self._samples) < self.MIN_SAMPLES:
            raise CalibrationError("calibration needs at least five complete samples")
        span = self._samples[-1][0] - self._samples[0][0]
        if span < self.MIN_SPAN_SECONDS:
            raise CalibrationError("calibration needs five seconds of stable samples")
        keys = list(self._samples[0][1])
        columns = {
            key: [sample[key] for _, sample in self._samples if key in sample] for key in keys
        }
        for key, values in columns.items():
            tolerance = self.MAX_STABLE_RANGE.get(key)
            if tolerance is not None and max(values) - min(values) > tolerance:
                raise CalibrationError(f"pose was unstable during capture: {key}")
        return Baseline(
            mode=self._mode,
            features={key: float(median(values)) for key, values in columns.items()},
            captured_at=self._clock(),
        )


class BaselineStore:
    """Keep seated and standing baselines separate; persist numbers only."""

    SCHEMA_VERSION = 1

    def __init__(self) -> None:
        self._baselines: dict[CalibrationMode, Baseline] = {}

    def set(self, baseline: Baseline) -> None:
        self._baselines[baseline.mode] = baseline

    def get(self, mode: CalibrationMode) -> Baseline | None:
        return self._baselines.get(mode)

    def clear(self) -> None:
        self._baselines.clear()

    def select(self, features: PostureFeatures) -> Baseline | None:
        """Return the baseline nearest to the current features, if any exist."""
        current = _flatten(features)
        best: Baseline | None = None
        best_distance = float("inf")
        for baseline in self._baselines.values():
            shared = baseline.features.keys() & current.keys()
            if not shared:
                continue
            distance = sum((baseline.features[key] - current[key]) ** 2 for key in shared)
            if distance < best_distance:
                best = baseline
                best_distance = distance
        return best

    def save(self, path: Path) -> None:
        """Atomically write schema-versioned numeric baselines to an explicit path."""
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "baselines": [
                {
                    "mode": baseline.mode.value,
                    "features": dict(baseline.features),
                    "captured_at": baseline.captured_at,
                }
                for baseline in self._baselines.values()
            ],
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        fd, temporary = tempfile.mkstemp(
            dir=path.parent, prefix=f"{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
        except BaseException:
            os.unlink(temporary)
            raise
        os.replace(temporary, path)

    @classmethod
    def load(cls, path: Path) -> BaselineStore:
        """Read baselines back, rejecting anything that is not strictly our schema."""
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CalibrationError(f"cannot read calibration file {path}") from exc
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "baselines"}:
            raise CalibrationError("calibration file has an unexpected shape")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise CalibrationError("unsupported calibration schema version")
        entries = payload["baselines"]
        if not isinstance(entries, list):
            raise CalibrationError("calibration baselines must be a list")
        store = cls()
        for entry in entries:
            store.set(_parse_baseline(entry))
        return store


def _parse_baseline(entry: object) -> Baseline:
    if not isinstance(entry, dict) or set(entry) != {"mode", "features", "captured_at"}:
        raise CalibrationError("calibration entry has an unexpected shape")
    try:
        mode = CalibrationMode(entry["mode"])
    except ValueError as exc:
        raise CalibrationError("calibration entry has an unknown mode") from exc
    raw_features = entry["features"]
    if not isinstance(raw_features, dict) or not raw_features:
        raise CalibrationError("calibration entry features must be a non-empty object")
    features: dict[str, float] = {}
    for key, value in raw_features.items():
        if not isinstance(key, str) or isinstance(value, bool):
            raise CalibrationError("calibration features must map strings to numbers")
        if not isinstance(value, int | float):
            raise CalibrationError("calibration features must map strings to numbers")
        features[key] = float(value)
    captured_at = entry["captured_at"]
    if isinstance(captured_at, bool) or not isinstance(captured_at, int | float):
        raise CalibrationError("calibration captured_at must be a number")
    return Baseline(mode=mode, features=features, captured_at=float(captured_at))
