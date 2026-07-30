# Posturely Mac Simulator Handoff

**Date:** 2026-07-30

## Current result

Posturely is implemented as a local Python 3.11 application with:

- A deterministic no-camera simulation of all three diagnostic lights.
- A live Mac camera path using OpenCV and MediaPipe Pose Landmarker.
- Three virtual head, shoulder, and torso lights.
- Exact off/amber/red/recovery timing.
- Confidence-gated posture geometry and absence handling.
- Optional numeric seated and standing calibration logic.
- No frame, landmark-history, or posture-history persistence.

The live app successfully opened camera index 0 after macOS Camera permission
was granted. MediaPipe initialized on the Apple M4, and the preview process
remained healthy. After accepting slightly out-of-frame landmark coordinates,
the live loop alternated between `waiting` and `healthy` without crashing,
confirming that pose inference and the complete posture pipeline were active.

## Verified

- 74 automated tests pass.
- Ruff reports no lint errors.
- Deterministic demo produces head, shoulder, torso, recovery, absence, and
  return-to-monitoring transitions.
- MediaPipe model construction succeeds outside the restricted sandbox.
- Camera permission and OpenCV capture initialization succeed.
- The recommended macOS launcher denies all process network access while
  preserving camera and Metal inference.
- Camera, pose backend, and preview resources close through context managers.
- Static privacy enforcement finds no frame-writing or server-listener APIs.
- The downloaded pose model is local and excluded from Git.

## Still needs Steve's live confirmation

- Pose points appear consistently when Steve is centered in frame.
- Each dot responds independently to a deliberate posture trial.
- Head and torso rules feel useful at Steve's actual desk angle.
- The shoulder proxy is useful enough to keep as rounding/imbalance rather
  than narrowing it to imbalance/elevation only.
- Seated and standing framing both work.

## Run

```bash
uv sync --python 3.11 --extra dev
uv run python scripts/fetch_pose_model.py
uv run python -m posturely.private_launch \
  --camera 0 \
  --model assets/models/pose_landmarker_lite.task
```

Press `q` or Escape in the preview window to stop. If the wrong camera opens,
try `--camera 1`.

## Known prototype gaps

- The numeric calibration engine is tested but not yet connected to live
  keyboard controls.
- Generic thresholds need desk-specific tuning.
- The preview currently analyzes every available Mac frame; Pi throttling and
  measured analyzed-FPS reporting are a later optimization.
- Raspberry Pi packaging, physical LEDs, CAD, and builder handoff have not
  started.
