"""Pure conversion from MediaPipe Pose Landmarker results to PoseFrame."""

from __future__ import annotations

from collections.abc import Callable
from types import TracebackType
from typing import Any

from posturely.core.types import Landmark, PoseFrame

_REQUIRED_LANDMARKS = {
    "nose": 0,
    "left_ear": 7,
    "right_ear": 8,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_hip": 23,
    "right_hip": 24,
}


class MediaPipePose:
    """Context-managed MediaPipe Tasks adapter with lazy native imports."""

    def __init__(
        self,
        model_path: str,
        *,
        backend_factory: Callable[[str], Any] | None = None,
        image_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self._backend = (
            backend_factory(model_path)
            if backend_factory is not None
            else _create_backend(model_path)
        )
        self._image_factory = image_factory or _create_image

    def detect(self, frame: Any, timestamp_ms: int) -> PoseFrame | None:
        image = self._image_factory(frame)
        result = self._backend.detect_for_video(image, timestamp_ms)
        return pose_frame_from_result(result, timestamp_ms / 1000.0)

    def close(self) -> None:
        self._backend.close()

    def __enter__(self) -> MediaPipePose:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _create_backend(model_path: str) -> Any:
    import mediapipe as mp

    options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        output_segmentation_masks=False,
    )
    return mp.tasks.vision.PoseLandmarker.create_from_options(options)


def _create_image(frame: Any) -> Any:
    import cv2
    import mediapipe as mp

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def pose_frame_from_result(result: Any, timestamp: float) -> PoseFrame | None:
    """Convert exactly one detected pose; ambiguous pose counts return None."""
    poses = getattr(result, "pose_landmarks", None) or []
    if len(poses) != 1:
        return None
    source = poses[0]
    landmarks = {
        name: Landmark(
            x=source[index].x,
            y=source[index].y,
            z=source[index].z,
            visibility=source[index].visibility,
            presence=source[index].presence,
        )
        for name, index in _REQUIRED_LANDMARKS.items()
    }
    return PoseFrame(landmarks=landmarks, captured_at=timestamp)
