# Posturely Prototype Completion Design

**Date:** 2026-07-30  
**Status:** Implemented; physical hardware acceptance remains unrun
**Owner:** Steve

## 1. Outcome

Complete Posturely as a convincing, privacy-preserving software prototype and
builder-ready appliance package. The result must make the live classifier
understandable, calibrate to a fixed desk setup without saving images, retain
the quiet three-light product behavior, and transfer cleanly to a Raspberry Pi
with physical LEDs.

The software simulation is the first acceptance gate. Pi integration,
electrical documentation, and enclosure work begin only after the complete
camera-free simulation passes its automated and visual checks.

This phase does not require Steve to perform another posture session. Automated
landmark scenarios validate all software behavior. A future live desk check is
useful for threshold tuning but is not a gate for completing this phase.

## 2. Product Principles

- The three small lights remain the product interface.
- Debug measurements appear only in the Mac developer preview.
- All inference stays local and every image frame remains memory-only.
- Calibration stores numerical posture features, never frames or landmarks.
- One shared posture engine powers the automated demo, Mac camera, and Pi.
- Generic thresholds remain usable when no calibration exists.
- The prototype makes awareness claims, not medical or diagnostic claims.
- No LLM, cloud inference, account, server, database, history, or custom model
  training is introduced.

## 3. Considered Approaches

### A. Instrument the shared posture pipeline — selected

Expose an immutable analysis snapshot from the existing application. The
snapshot contains current features, evidence scores, alert timing progress,
monitoring health, detected desk mode, and calibration status. The Mac preview
renders it, while the synthetic demo and Pi output adapters consume the same
state.

This adds the least architecture and proves the real engine rather than a
facsimile.

### B. Build a separate polished demo dashboard

A standalone dashboard could look richer quickly, but it could diverge from
live behavior and conceal camera/classifier problems. It is rejected.

### C. Train a classifier before polishing the prototype

A trained model could eventually improve difficult shoulder cases, but it
requires labeled personal data and evaluation work before the deterministic
geometry has been tuned. It is rejected for this phase.

## 4. Runtime Data Flow

For each analyzed frame:

1. The camera or deterministic demo produces an in-memory frame.
2. The pose adapter produces one in-memory `PoseFrame`, or no pose.
3. The feature extractor produces normalized head, shoulder, and torso values.
4. The mode estimator classifies the fixed desk view as seated, standing, or
   uncertain from stable screen-relative body position.
5. The baseline store chooses the matching calibrated mode when available.
6. The evaluator calculates independent normalized issue scores. A score below
   `1.0` is acceptable; a score at or above `1.0` is problematic.
7. The temporal state machine produces light colors and timing progress. Brief
   tracking gaps pause timers; a real absence clears them.
8. The application publishes one immutable `AnalysisSnapshot`.
9. The active output adapter renders the Mac preview or drives the Pi LEDs.

No stage persists a frame, landmark history, posture-event history, or score
history. Bounded numeric samples exist in memory only for mode voting, FPS
measurement, and a five-second calibration, then are discarded.

## 5. Developer Preview

The preview remains a single OpenCV window. It contains:

- The mirrored camera frame or synthetic demo canvas.
- Pose landmarks, toggleable with `l`.
- Three compact head, shoulder, and torso light dots.
- For each category:
  - normalized score such as `0.72` or `1.31`;
  - a plain-language status: `OK`, `5s warning`, `15s alert`, or `uncertain`;
  - countdown/progress to amber and red while an issue persists;
  - the evaluator reason in developer mode.
- Current mode: `seated`, `standing`, or `generic`.
- Calibration state and instructions.
- Actual rolling analyzed FPS.
- Monitoring health.

Developer details are toggleable with `d`. They are enabled by default on the
Mac and absent from the final physical appliance.

The automatic `posturely --demo` run uses this exact preview and exact engine.
It continues to cycle all three categories without a camera and closes after
the scripted sequence. It shows scores and countdowns so a viewer can see why
each light changes.

## 6. Timing and Confidence

Each category retains the established behavior:

- Below five continuous problematic seconds: off.
- Five to under 15 problematic seconds: amber.
- At least 15 problematic seconds: red.
- Two corrected seconds: off.

An `IssueProgress` value exposes problematic elapsed time, corrected elapsed
time, and seconds until the next transition. It is observational only; the
state machine remains the sole timing authority.

A tracking or metric-confidence gap of under one second pauses timing without
clearing the light. A gap of at least one second clears the affected timer. An
application that starts without a person reports `waiting` immediately.

## 7. Calibration and Mode Selection

Calibration is optional and local:

- Press `c` to start a five-second capture.
- The current stable mode is chosen automatically.
- When automatic mode is uncertain, the preview asks for `1` (seated) or `2`
  (standing); it never guesses and stores a mislabeled baseline.
- During capture, the preview shows progress and accepts only complete,
  confident feature samples.
- On success, the median numeric baseline is stored atomically in the selected
  calibration file.
- On failure, the previous baseline remains intact and the preview shows the
  precise reason.
- Press `x`, then `x` again within three seconds, to clear both baselines.
  This confirmation prevents accidental deletion.

The Mac default path is `.posturely-calibration.json`, which is git-ignored.
`--calibration-file PATH` selects another explicit location.

The calibrated evaluator compares current values with the selected baseline:

- Head score uses excess horizontal displacement and neck-angle change.
- Shoulder score uses line-angle/asymmetry change, increased elbow inset, and
  decreased apparent shoulder-width ratio when available.
- Torso score uses lean-angle change and compression decrease.

Every threshold remains named, conservative, and testable. If no matching
baseline exists, generic thresholds apply.

Mode estimation uses a small rolling vote over reliable pose frames, based on
the shoulder and hip vertical positions in the fixed camera view. It does not
infer a medical body state. Until stable, the system reports `generic` and uses
generic thresholds.

## 8. Raspberry Pi and LED Boundary

The portable application emits an `OutputState`; it never imports GPIO code.
A hardware-output protocol maps:

- head, shoulders, torso `off/amber/red` to three RGB LEDs;
- `healthy` to a dim steady white monitoring LED;
- `waiting` to a slow white pulse;
- `fault` to a fast white pulse;
- calibration capture to blue diagnostic pulses.

The Pi adapter lazily imports its GPIO library so Mac development and CI need
no Pi dependency. A fake adapter verifies pin mapping, color mapping, pulse
timing, and cleanup.

The builder package includes:

- Raspberry Pi launch command and systemd service template.
- Pin map and wiring diagram with current-limiting resistor guidance.
- Costed bill of materials with controlled camera fallbacks.
- Parametric OpenSCAD concept enclosure for the approved slim column.
- Camera, LED, button, ventilation, USB-C, ballast, and service-panel cutouts.
- Assembly and software provisioning checklist.
- Acceptance-test checklist.

The CAD remains parameterized until exact purchased camera, LED, button, and
fastener dimensions are measured. It is a printable concept and contractor
starting point, not a claim of production-ready mechanical fit.

## 9. Error Handling

- Missing pose at startup: show `waiting`; no posture alert.
- Brief pose loss: pause timers and preserve current state.
- Sustained pose loss: clear timers and show `waiting`.
- One uncertain metric: suppress or clear only that category.
- Camera or model failure: show `fault`, return a nonzero process status, and
  release camera/model/window resources.
- Invalid calibration file: keep generic operation, display a warning, and do
  not overwrite the file automatically.
- Unstable or incomplete calibration: reject the capture and preserve the old
  baseline.
- Pi GPIO failure: turn off diagnostic outputs when possible and surface a
  fault to the supervisor.

## 10. Privacy

- Camera frames are processed in memory and discarded.
- Landmarks, snapshots, scores, and posture events are never persisted.
- Calibration JSON contains only schema version, mode, numeric medians, and
  capture timestamp.
- The private macOS launcher continues to deny all outbound network access.
- Product source contains no frame-writing, video-writing, HTTP-listener, or
  telemetry path.
- Debug console output reports state transitions and operational errors only.

## 11. Verification

Automated tests must prove:

- Score normalization and generic/calibrated evaluator behavior.
- Seated, standing, and uncertain mode stabilization.
- Exact progress/countdown values at timing boundaries.
- Calibration start, progress, success, rejection, persistence, selection, and
  confirmed clearing.
- Preview layout derives every score, status, and countdown from the immutable
  analysis snapshot.
- Automatic visual demo reaches amber and red for every category.
- Measured FPS is nonzero after multiple samples.
- Pi output mapping and cleanup work without a GPIO dependency.
- No camera, native preview, Pi hardware, network, or sleeping is required in
  CI.
- Privacy scans and calibration serialization remain compliant.

Manual smoke checks in this phase are camera-free:

- Run the visual demo to completion.
- Confirm each light, score, countdown, mode label, and monitoring transition
  appears.
- Render the OpenSCAD file if OpenSCAD is installed; otherwise validate its
  syntax and parameter documentation without claiming a rendered STL.

## 12. Completion Criteria

This phase is complete when:

- The live path exposes understandable scores and timing progress.
- Calibration is connected end to end and changes evaluator behavior.
- The automatic demo visibly exercises the completed interface.
- The Mac app retains its network-denied launch path.
- A Pi LED adapter and builder package are present and tested.
- The public repository documentation matches actual behavior.
- The full test suite, lint, privacy checks, demo smoke test, and GitHub CI pass.
