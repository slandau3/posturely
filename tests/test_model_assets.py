from __future__ import annotations

import io

from posturely.model_assets import download_pose_model


class FakeResponse(io.BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_model_download_is_atomic_and_reuses_valid_existing_file(tmp_path) -> None:
    destination = tmp_path / "pose.task"
    calls = 0
    payload = b"model" * 300_000

    def opener(_url: str) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse(payload)

    assert download_pose_model(destination, opener=opener) == destination
    assert destination.read_bytes() == payload
    assert calls == 1

    assert download_pose_model(destination, opener=opener) == destination
    assert calls == 1
