"""One-time download support for the local MediaPipe pose model."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import urlopen

POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
_MINIMUM_MODEL_BYTES = 1_000_000


def download_pose_model(
    destination: Path,
    *,
    opener: Callable[[str], Any] = urlopen,
) -> Path:
    """Download atomically unless a plausibly valid model already exists."""
    if destination.is_file() and destination.stat().st_size >= _MINIMUM_MODEL_BYTES:
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f"{destination.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(file_descriptor, "wb") as output, opener(POSE_MODEL_URL) as response:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        if os.path.getsize(temporary_name) < _MINIMUM_MODEL_BYTES:
            raise ValueError("downloaded pose model is unexpectedly small")
        os.replace(temporary_name, destination)
    except BaseException:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise
    return destination
