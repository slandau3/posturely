from __future__ import annotations

import re
from pathlib import Path

from posturely.adapters.pi_leds import PiLedOutput

ROOT = Path(__file__).parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_wiring_guide_matches_every_software_pin() -> None:
    wiring = read("hardware/wiring.md")
    pins = {
        *PiLedOutput.HEAD_PINS,
        *PiLedOutput.SHOULDERS_PINS,
        *PiLedOutput.TORSO_PINS,
        PiLedOutput.MONITOR_PIN,
        PiLedOutput.BUTTON_PIN,
    }

    for pin in pins:
        assert f"BCM {pin}" in wiring


def test_service_uses_real_posturely_cli_options() -> None:
    service = read("deploy/posturely.service")

    assert "posturely --camera 0" in service
    assert "--model /opt/posturely/assets/models/pose_landmarker_lite.task" in service
    assert "--no-preview" in service
    assert "--pi-leds" in service


def test_parametric_column_contains_every_required_cutout() -> None:
    cad = read("hardware/posturely-column.scad")

    for token in (
        "column_height = 180",
        "column_width = 65",
        "column_depth = 72",
        "camera_cutout",
        "diagnostic_apertures",
        "monitor_aperture",
        "button_cutout",
        "usb_c_cutout",
        "ventilation",
        "ballast_pocket",
        "rear_panel",
        "light_barriers",
    ):
        assert token in cad


def test_bom_and_acceptance_checklist_are_complete() -> None:
    bom = read("hardware/bom.md")
    assembly = read("hardware/assembly.md").lower()
    match = re.search(r"expected parts total[^$]*\$(\d+)[–-]\$(\d+)", bom.lower())

    assert match is not None
    low, high = (int(value) for value in match.groups())
    assert low >= 90
    assert high <= 150
    for item in (
        "cold boot",
        "eight-hour",
        "thermal",
        "camera",
        "led",
        "calibration",
        "network",
        "power recovery",
    ):
        assert item in assembly
