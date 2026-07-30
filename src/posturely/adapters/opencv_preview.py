"""Pure layout for the on-screen diagnostic lights."""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Any

from posturely.core.types import DiagnosticColor, MonitoringState, OutputState, PoseFrame

_BGR_BY_COLOR = {
    DiagnosticColor.OFF: (70, 70, 70),
    DiagnosticColor.AMBER: (0, 215, 255),
    DiagnosticColor.RED: (60, 60, 220),
}


@dataclass(frozen=True, slots=True)
class DiagnosticLight:
    label: str
    center: tuple[int, int]
    radius: int
    color: tuple[int, int, int]


class OpenCVPreview:
    """Draw a private developer preview; OpenCV is loaded only on construction."""

    WINDOW_NAME = "Posturely"

    def __init__(self, *, cv2_module: Any | None = None) -> None:
        if cv2_module is None:
            import cv2

            cv2_module = cv2
        self._cv2 = cv2_module

    def render(
        self,
        *,
        frame: Any,
        pose: PoseFrame | None,
        state: OutputState,
        fps: float,
        mirror: bool,
    ) -> int:
        cv2 = self._cv2
        canvas = cv2.flip(frame, 1) if mirror else frame
        height, width = canvas.shape[:2]
        for light in diagnostic_lights(state, width=width, height=height):
            cv2.circle(canvas, light.center, light.radius, light.color, -1)
            label_origin = (light.center[0] + light.radius + 8, light.center[1] + 5)
            cv2.putText(
                canvas,
                light.label,
                label_origin,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (235, 235, 235),
                1,
                cv2.LINE_AA,
            )
        _draw_pose(cv2, canvas, pose, width, height, mirror)
        monitoring_color = {
            MonitoringState.HEALTHY: (220, 220, 220),
            MonitoringState.WAITING: (120, 120, 120),
            MonitoringState.FAULT: (60, 60, 220),
        }[state.monitoring]
        cv2.circle(canvas, (width - 24, height - 24), 6, monitoring_color, -1)
        cv2.putText(
            canvas,
            f"{fps:.1f} analyzed FPS",
            (width - 170, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (230, 230, 230),
            1,
            cv2.LINE_AA,
        )
        cv2.imshow(self.WINDOW_NAME, canvas)
        return cv2.waitKey(1) & 0xFF

    def close(self) -> None:
        self._cv2.destroyWindow(self.WINDOW_NAME)

    def __enter__(self) -> OpenCVPreview:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def diagnostic_lights(
    state: OutputState, *, width: int, height: int
) -> list[DiagnosticLight]:
    """Lay out head, shoulders, and torso lights top-to-bottom."""
    radius = max(4, min(width, height) // 32)
    x = radius * 2
    labels = ("head", "shoulders", "torso")
    colors = (state.head, state.shoulders, state.torso)
    ys = (height // 4, height // 2, 3 * height // 4)
    return [
        DiagnosticLight(
            label=label,
            center=(x, y),
            radius=radius,
            color=_BGR_BY_COLOR[color],
        )
        for label, color, y in zip(labels, colors, ys, strict=True)
    ]


def _draw_pose(
    cv2: Any,
    canvas: Any,
    pose: PoseFrame | None,
    width: int,
    height: int,
    mirror: bool,
) -> None:
    if pose is None:
        return
    for point in pose.landmarks.values():
        x = int((1.0 - point.x if mirror else point.x) * width)
        y = int(point.y * height)
        cv2.circle(canvas, (x, y), 3, (255, 180, 80), -1)
