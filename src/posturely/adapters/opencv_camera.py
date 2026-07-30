"""Webcam frame source backed by OpenCV with a lazy native import."""

from __future__ import annotations

from types import TracebackType
from typing import Any

_FRAME_WIDTH = 640
_FRAME_HEIGHT = 480
_WARMUP_ATTEMPTS = 5


class OpenCVCamera:
    """Context-managed camera handle with warmup and explicit fault reporting."""

    def __init__(self, index: int) -> None:
        self.index = index
        self.fault: str | None = None
        self._capture: Any | None = None

    def open(self) -> OpenCVCamera:
        """Open the device, request 640x480, and wait for a first real frame."""
        import cv2

        capture = cv2.VideoCapture(self.index)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, _FRAME_WIDTH)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, _FRAME_HEIGHT)
        self._capture = capture
        for _ in range(_WARMUP_ATTEMPTS):
            ok, _frame = capture.read()
            if ok:
                return self
        self.fault = f"camera {self.index} produced no frame during warmup"
        return self

    def read(self) -> Any | None:
        """Return the latest frame, or None while recording an explicit fault."""
        if self._capture is None or self.fault is not None:
            return None
        ok, frame = self._capture.read()
        if not ok:
            self.fault = f"camera {self.index} read failed"
            return None
        return frame

    def close(self) -> None:
        """Release the underlying capture device exactly once."""
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()

    def __enter__(self) -> OpenCVCamera:
        return self.open()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
