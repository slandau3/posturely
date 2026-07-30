#!/usr/bin/env python3
"""Fetch Posturely's local MediaPipe model into the ignored assets directory."""

from pathlib import Path

from posturely.model_assets import download_pose_model


def main() -> int:
    destination = Path("assets/models/pose_landmarker_lite.task")
    print(download_pose_model(destination))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
