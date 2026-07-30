"""Contract tests for the live camera, pose-conversion, preview, and CLI wiring."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable

import pytest

from posturely.__main__ import main
from posturely.adapters.mediapipe_pose import MediaPipePose, pose_frame_from_result
from posturely.adapters.opencv_camera import OpenCVCamera
from posturely.adapters.opencv_preview import OpenCVPreview, diagnostic_lights
from posturely.core.types import DiagnosticColor, MonitoringState, OutputState


def test_adapter_modules_import_without_native_libraries() -> None:
    """Importing adapter contracts must not load cv2 or mediapipe."""
    assert "cv2" not in sys.modules
    assert "mediapipe" not in sys.modules


class FakeCapture:
    def __init__(self, reads: list[tuple[bool, object]]) -> None:
        self._reads = list(reads)
        self.set_calls: list[tuple[int, float]] = []
        self.released = False

    def set(self, prop: int, value: float) -> bool:
        self.set_calls.append((prop, value))
        return True

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, object]:
        if self._reads:
            return self._reads.pop(0)
        return True, object()

    def release(self) -> None:
        self.released = True


def install_fake_cv2(
    monkeypatch: pytest.MonkeyPatch, capture: FakeCapture
) -> types.SimpleNamespace:
    opened_indexes: list[int] = []

    def video_capture(index: int) -> FakeCapture:
        opened_indexes.append(index)
        return capture

    fake = types.SimpleNamespace(
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
        VideoCapture=video_capture,
        opened_indexes=opened_indexes,
    )
    monkeypatch.setitem(sys.modules, "cv2", fake)
    return fake


def _fake_mp_landmark(x: float) -> types.SimpleNamespace:
    return types.SimpleNamespace(x=x, y=0.5, z=0.0, visibility=0.9, presence=0.8)


def _fake_pose_result(pose_count: int) -> types.SimpleNamespace:
    landmarks = [_fake_mp_landmark(x=index / 100) for index in range(33)]
    return types.SimpleNamespace(pose_landmarks=[landmarks for _ in range(pose_count)])


class TestOpenCVCamera:
    def test_configures_640x480_on_the_requested_index(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capture = FakeCapture(reads=[(True, object())])
        fake_cv2 = install_fake_cv2(monkeypatch, capture)

        with OpenCVCamera(index=1) as camera:
            assert camera.fault is None

        assert fake_cv2.opened_indexes == [1]
        assert (fake_cv2.CAP_PROP_FRAME_WIDTH, 640) in capture.set_calls
        assert (fake_cv2.CAP_PROP_FRAME_HEIGHT, 480) in capture.set_calls

    def test_tolerates_initial_empty_frames(self, monkeypatch: pytest.MonkeyPatch) -> None:
        capture = FakeCapture(reads=[(False, None), (False, None), (True, object())])
        install_fake_cv2(monkeypatch, capture)

        with OpenCVCamera(index=0) as camera:
            assert camera.fault is None

    def test_reports_read_failure_as_an_explicit_fault(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capture = FakeCapture(reads=[(True, object()), (False, None)])
        install_fake_cv2(monkeypatch, capture)

        with OpenCVCamera(index=0) as camera:
            assert camera.read() is None
            assert camera.fault is not None

    def test_faults_when_no_warmup_frame_ever_arrives(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        capture = FakeCapture(reads=[(False, None)] * 10)
        install_fake_cv2(monkeypatch, capture)

        camera = OpenCVCamera(index=0)
        camera.open()
        try:
            assert camera.fault is not None
        finally:
            camera.close()
        assert capture.released

    def test_always_releases_the_capture(self, monkeypatch: pytest.MonkeyPatch) -> None:
        capture = FakeCapture(reads=[(True, object())])
        install_fake_cv2(monkeypatch, capture)

        with pytest.raises(RuntimeError, match="boom"), OpenCVCamera(index=0):
            raise RuntimeError("boom")

        assert capture.released


EXPECTED_LANDMARK_INDEXES = {
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


class TestPoseResultConversion:
    def test_maps_required_landmarks_with_visibility_and_presence(self) -> None:
        frame = pose_frame_from_result(_fake_pose_result(pose_count=1), timestamp=1.25)

        assert frame is not None
        assert frame.captured_at == 1.25
        assert set(frame.landmarks) == set(EXPECTED_LANDMARK_INDEXES)
        for name, index in EXPECTED_LANDMARK_INDEXES.items():
            landmark = frame.landmarks[name]
            assert landmark.x == pytest.approx(index / 100)
            assert landmark.y == pytest.approx(0.5)
            assert landmark.visibility == pytest.approx(0.9)
            assert landmark.presence == pytest.approx(0.8)

    def test_returns_none_when_no_pose_is_detected(self) -> None:
        assert pose_frame_from_result(_fake_pose_result(pose_count=0), timestamp=0.0) is None

    def test_returns_none_when_multiple_poses_are_detected(self) -> None:
        assert pose_frame_from_result(_fake_pose_result(pose_count=2), timestamp=0.0) is None

    def test_pose_adapter_detects_converts_and_closes_backend(self) -> None:
        result = _fake_pose_result(pose_count=1)

        class Backend:
            closed = False
            calls: list[tuple[object, int]] = []

            def detect_for_video(self, image: object, timestamp_ms: int):
                self.calls.append((image, timestamp_ms))
                return result

            def close(self) -> None:
                self.closed = True

        backend = Backend()
        adapter = MediaPipePose(
            "pose.task",
            backend_factory=lambda _path: backend,
            image_factory=lambda frame: ("image", frame),
        )
        frame = object()

        pose = adapter.detect(frame, 1250)
        adapter.close()

        assert pose is not None
        assert pose.captured_at == pytest.approx(1.25)
        assert backend.calls == [(("image", frame), 1250)]
        assert backend.closed


COLOR_BY_DIAGNOSTIC = {
    DiagnosticColor.OFF: (70, 70, 70),
    DiagnosticColor.AMBER: (0, 215, 255),
    DiagnosticColor.RED: (60, 60, 220),
}


def _output_state(color: DiagnosticColor) -> OutputState:
    return OutputState(
        head=color,
        shoulders=color,
        torso=color,
        monitoring=MonitoringState.HEALTHY,
    )


class TestDiagnosticLights:
    def test_three_labeled_lights_in_head_shoulder_torso_order(self) -> None:
        lights = diagnostic_lights(_output_state(DiagnosticColor.OFF), width=640, height=480)

        assert [light.label for light in lights] == ["head", "shoulders", "torso"]
        centers_y = [light.center[1] for light in lights]
        assert centers_y == sorted(centers_y)
        for light in lights:
            assert 0 <= light.center[0] < 640
            assert 0 <= light.center[1] < 480
            assert light.radius > 0

    @pytest.mark.parametrize(
        ("color", "expected_bgr"), list(COLOR_BY_DIAGNOSTIC.items())
    )
    def test_color_maps_diagnostic_state_to_bgr(
        self, color: DiagnosticColor, expected_bgr: tuple[int, int, int]
    ) -> None:
        lights = diagnostic_lights(_output_state(color), width=640, height=480)

        assert [light.color for light in lights] == [expected_bgr] * 3

    def test_preview_draws_lights_returns_key_and_closes_window(self) -> None:
        class Frame:
            shape = (480, 640, 3)

        class FakeCV2:
            FONT_HERSHEY_SIMPLEX = 0
            LINE_AA = 1

            def __init__(self) -> None:
                self.circles: list[tuple[object, tuple[int, int], int, object, int]] = []
                self.shown: list[tuple[str, object]] = []
                self.destroyed: list[str] = []

            def flip(self, frame: object, axis: int) -> object:
                return frame

            def circle(self, *args: object) -> None:
                self.circles.append(args)  # type: ignore[arg-type]

            def putText(self, *args: object) -> None:
                return None

            def imshow(self, name: str, frame: object) -> None:
                self.shown.append((name, frame))

            def waitKey(self, _delay: int) -> int:
                return ord("q")

            def destroyWindow(self, name: str) -> None:
                self.destroyed.append(name)

        fake_cv2 = FakeCV2()
        preview = OpenCVPreview(cv2_module=fake_cv2)

        key = preview.render(
            frame=Frame(),
            pose=None,
            state=_output_state(DiagnosticColor.AMBER),
            fps=5.0,
            mirror=True,
        )
        preview.close()

        assert key == ord("q")
        assert len(fake_cv2.circles) >= 3
        assert fake_cv2.shown
        assert fake_cv2.destroyed == ["Posturely"]


def _recording_live(calls: list[object]) -> Callable[[object], int]:
    def fake_live(args: object) -> int:
        calls.append(args)
        return 0

    return fake_live


class TestLiveCliWiring:
    def test_live_mode_requires_a_model(self) -> None:
        with pytest.raises(SystemExit) as excinfo:
            main(["--camera", "0"], live=_recording_live([]))

        assert excinfo.value.code == 2

    def test_live_mode_requires_an_existing_model_path(self, tmp_path) -> None:
        calls: list[object] = []
        missing = tmp_path / "missing.task"

        with pytest.raises(SystemExit) as excinfo:
            main(["--camera", "0", "--model", str(missing)], live=_recording_live(calls))

        assert excinfo.value.code == 2
        assert calls == []

    def test_live_mode_dispatches_to_the_injected_runner(self, tmp_path) -> None:
        model = tmp_path / "pose.task"
        model.write_bytes(b"stub")
        calls: list[object] = []

        exit_code = main(
            ["--camera", "1", "--model", str(model), "--no-mirror", "--no-preview"],
            live=_recording_live(calls),
        )

        assert exit_code == 0
        (args,) = calls
        assert args.camera == 1
        assert args.model == str(model)
        assert args.mirror is False
        assert args.no_preview is True
        assert "cv2" not in sys.modules
        assert "mediapipe" not in sys.modules

    def test_live_mode_lazily_dispatches_to_default_runner(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        model = tmp_path / "pose.task"
        model.write_bytes(b"stub")
        calls: list[object] = []

        def fake_run_live(args: object) -> int:
            calls.append(args)
            return 7

        monkeypatch.setattr("posturely.live.run_live", fake_run_live)

        assert main(["--camera", "0", "--model", str(model)]) == 7
        assert len(calls) == 1
