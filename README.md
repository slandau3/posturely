# Posturely

Posturely is a privacy-first posture monitor that runs entirely on your own
computer. The Mac prototype reads a webcam in memory, estimates a single pose,
and drives three quiet virtual lights:

- Head and neck drift
- Shoulder imbalance or inward-rounding proxy
- Whole-torso slump or excessive lean

Each light stays off for brief movement, turns amber after five continuous
seconds, turns red after 15 seconds, and clears after two corrected seconds.

Posturely is an awareness tool, not a medical device. A single camera cannot
reliably diagnose anatomy, and shoulder rounding is the least certain metric.

## Privacy

- Frames are processed locally and discarded.
- No image, video, landmark history, or posture history is written.
- No cloud inference, account, telemetry, or network listener is used.
- The downloaded `.task` file is a pose model, not captured data.

The automated privacy test rejects common image/video-writing and server APIs.

## Run on a Mac

Requirements: macOS on Apple silicon, Python 3.11, and
[uv](https://docs.astral.sh/uv/).

```bash
uv sync --python 3.11 --extra dev
uv run python scripts/fetch_pose_model.py
uv run python -m posturely.private_launch \
  --camera 0 \
  --model assets/models/pose_landmarker_lite.task
```

On first launch, grant Camera access to the terminal or desktop app running
Posturely. Press `q` or Escape in the preview window to quit.

If camera index `0` is not the desired webcam, try `--camera 1`.

Google's current MediaPipe Tasks privacy notice says the library sends API
performance and utilization metrics (not input images) to Google. The macOS
`private_launch` command above runs Posturely inside an operating-system
sandbox with `(deny network*)`, preventing those metrics—or any other outbound
traffic—from leaving the process. Do not replace that command with a raw
`posturely` launch if you require zero network access.

## Run without a camera

Open an accelerated visual simulation of the finished appliance:

```bash
uv run posturely --demo
```

It uses the real posture engine with a synthetic person, automatically cycles
the head, shoulder, and torso lights through amber and red, then demonstrates
absence/recovery. It runs at 10x speed, takes about seven seconds, and never
opens the camera. Press `q` or Escape to quit early.

For text-only output without an OpenCV window:

```bash
uv run posturely --demo --no-preview --demo-seconds 70
```

It prints only state transitions such as `head: off -> amber`.

## Test

```bash
uv run pytest -q
uv run ruff check src tests scripts
```

The headless suite uses synthetic landmarks and fake native adapters; CI never
requests a camera.

## Architecture

`src/posturely/core/` contains the portable geometry, evaluator, alert timing,
and numeric calibration logic. It imports neither OpenCV nor MediaPipe.
`src/posturely/adapters/` owns replaceable Mac camera, pose, and preview
integration. `src/posturely/live.py` wires the camera path together, while
`src/posturely/demo_ui.py` drives the same engine without a camera.

The same core is intended to transfer to a low-cost Raspberry Pi appliance
with three tiny physical LEDs and no display.

## Current prototype limits

- Generic thresholds still need real-desk tuning.
- The optional numeric calibration engine exists, but its live keyboard/button
  interaction is not yet connected.
- Seated/standing mode selection and Raspberry Pi GPIO/CAD are later stages.
- Multi-person scenes are deliberately treated as uncertain.

See the approved design in
`docs/superpowers/specs/2026-07-30-posture-monitor-design.md`.
