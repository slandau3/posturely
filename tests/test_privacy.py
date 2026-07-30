from __future__ import annotations

from pathlib import Path


def test_product_source_contains_no_frame_persistence_or_network_server_apis() -> None:
    """Adding a frame writer or listener would violate Posturely's core promise."""
    source_root = Path("src/posturely")
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.rglob("*.py"))
    forbidden = (
        "imwrite(",
        "VideoWriter(",
        "imencode(",
        "pickle.dump(",
        "socket.listen(",
        "HTTPServer(",
    )

    assert not [token for token in forbidden if token in source]


def test_portable_core_contains_no_native_or_gpio_imports() -> None:
    core = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/posturely/core").rglob("*.py")
    )

    assert "import cv2" not in core
    assert "import mediapipe" not in core
    assert "import gpiozero" not in core


def test_readme_documents_completed_simulator_privacy_and_hardware_status() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for text in (
        "scores, reasons, and countdowns",
        ".posturely-calibration.json",
        "--pi-leds",
        "hardware/posturely-column.scad",
        "not a medical device",
    ):
        assert text in readme
