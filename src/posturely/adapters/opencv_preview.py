"""Pure layout for the on-screen diagnostic lights."""

from __future__ import annotations

from dataclasses import dataclass
from types import TracebackType
from typing import Any

from posturely.core.analysis import AnalysisSnapshot, IssueProgress
from posturely.core.types import (
    DiagnosticColor,
    Evidence,
    MonitoringState,
    OutputState,
    PoseFrame,
)

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


@dataclass(frozen=True, slots=True)
class DiagnosticRow:
    label: str
    score: float
    status: str
    countdown: str
    reason: str


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
        status_text: str | None = None,
        snapshot: AnalysisSnapshot | None = None,
        show_landmarks: bool = True,
        show_details: bool = True,
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
        if show_landmarks:
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
        if status_text:
            cv2.putText(
                canvas,
                status_text,
                (width // 2 - 145, height - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (180, 180, 180),
                1,
                cv2.LINE_AA,
            )
        if snapshot is not None and show_details:
            _draw_details(cv2, canvas, snapshot, width, height)
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


def diagnostic_rows(snapshot: AnalysisSnapshot) -> list[DiagnosticRow]:
    """Convert analysis into compact, presentation-neutral developer rows."""
    rows: list[DiagnosticRow] = []
    for label in ("head", "shoulders", "torso"):
        evidence = getattr(snapshot.evidence, label)
        progress = getattr(snapshot.progress, label)
        color = getattr(snapshot.state, label)
        status, countdown = _row_status(evidence, progress, color)
        rows.append(
            DiagnosticRow(
                label=label,
                score=evidence.magnitude,
                status=status,
                countdown=countdown,
                reason=evidence.reason,
            )
        )
    return rows


def _row_status(
    evidence: Evidence,
    progress: IssueProgress,
    color: DiagnosticColor,
) -> tuple[str, str]:
    if not evidence.confident:
        return ("uncertain", "")
    if progress.corrected_seconds > 0.0:
        remaining = progress.next_transition_seconds
        return ("correcting", f"clear in {remaining:.1f}s" if remaining is not None else "")
    if color is DiagnosticColor.RED:
        return ("15s alert", "")
    if color is DiagnosticColor.AMBER:
        remaining = progress.next_transition_seconds
        return ("5s warning", f"red in {remaining:.1f}s" if remaining is not None else "")
    if evidence.problematic:
        remaining = progress.next_transition_seconds
        return ("checking", f"amber in {remaining:.1f}s" if remaining is not None else "")
    return ("OK", "")


def _draw_details(
    cv2: Any,
    canvas: Any,
    snapshot: AnalysisSnapshot,
    width: int,
    height: int,
) -> None:
    for index, row in enumerate(diagnostic_rows(snapshot)):
        y = (height // 4, height // 2, 3 * height // 4)[index]
        summary = f"{row.score:.2f}  {row.status}"
        if row.countdown:
            summary += f"  {row.countdown}"
        cv2.putText(
            canvas,
            summary,
            (90, y + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (240, 240, 240),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            row.reason,
            (90, y + 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.36,
            (160, 160, 160),
            1,
            cv2.LINE_AA,
        )
    baseline = (
        f" · {snapshot.baseline_mode.value} calibrated"
        if snapshot.baseline_mode is not None
        else " · generic thresholds"
    )
    cv2.putText(
        canvas,
        f"mode: {snapshot.mode.value}{baseline}",
        (width - 280, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.4,
        (210, 210, 210),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        snapshot.calibration.message,
        (width - 300, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.36,
        (180, 180, 180),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "c calibrate · 1 seated · 2 standing · x clear · l landmarks · d details · q quit",
        (12, height - 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.30,
        (145, 145, 145),
        1,
        cv2.LINE_AA,
    )


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
