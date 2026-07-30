# Posturely Mac Simulator Handoff

**Date:** 2026-07-30

## Current result

Posturely is implemented as a local Python 3.11 application with:

- An automatic visual, camera-free simulation of all three diagnostic lights.
- A live Mac camera path using OpenCV and MediaPipe Pose Landmarker.
- Three virtual head, shoulder, and torso lights.
- Exact off/amber/red/recovery timing.
- Live normalized scores, evaluator reasons, and transition countdowns.
- Confidence-gated posture geometry and dropout-tolerant absence handling.
- End-to-end numeric seated and standing calibration and mode selection.
- A tested Pi LED boundary plus builder BOM, wiring, service, assembly, and
  parametric slim-column package.
- No frame, landmark-history, or posture-history persistence.

The live app successfully opened camera index 0 after macOS Camera permission
was granted. MediaPipe initialized on the Apple M4, and the preview process
remained healthy. After accepting slightly out-of-frame landmark coordinates,
the live loop alternated between `waiting` and `healthy` without crashing,
confirming that pose inference and the complete posture pipeline were active.

The one-second dropout grace period pauses posture timers during momentary
landmark loss instead of repeatedly erasing them. A real absence still clears
the lights and reports `waiting`.

## Software simulator verified

- 127 automated tests pass.
- Ruff reports no lint errors.
- The visual demo automatically displays head, shoulder, torso, recovery,
  seated/standing, absence, and return-to-monitoring transitions using the
  real engine.
- The overlay derives every score, reason, and countdown from the same immutable
  analysis snapshot used by live monitoring.
- Baseline-relative evaluation, capture rejection, atomic numeric persistence,
  mode selection, and confirmed clearing are covered by automated tests.
- MediaPipe model construction succeeds outside the restricted sandbox.
- Camera permission and OpenCV capture initialization succeed.
- The recommended macOS launcher denies all process network access while
  preserving camera and Metal inference.
- Camera, pose backend, and preview resources close through context managers.
- Static privacy enforcement finds no frame-writing or server-listener APIs.
- The downloaded pose model is local and excluded from Git.

## Builder package status

- The Pi adapter maps the shared output state to three RGB diagnostics and a
  pulsing monitoring LED, imports GPIO lazily, and is tested with fake hardware.
- Software pins, wiring documentation, service options, BOM range, CAD
  parameters, and acceptance checklist are checked for consistency.
- OpenSCAD is not installed on this Mac, so no rendered STL is claimed.
- No physical Pi, camera, LED circuit, enclosure print, thermal run, or
  electrical acceptance test has been performed.

## Run

To verify the concept without a camera:

```bash
uv run posturely --demo
```

The entire light sequence completes automatically in about seven seconds.

For live monitoring:

```bash
uv sync --python 3.11 --extra dev
uv run python scripts/fetch_pose_model.py
uv run python -m posturely.private_launch \
  --camera 0 \
  --model assets/models/pose_landmarker_lite.task
```

Press `q` or Escape in the preview window to stop. If the wrong camera opens,
try `--camera 1`.

## Remaining physical validation

- Generic thresholds need desk-specific tuning.
- Exact procured-part dimensions must be entered before STL export.
- Pi throughput, eight-hour stability, thermals, wiring, button integration,
  privacy shutter, and power recovery remain acceptance checks for the builder.
