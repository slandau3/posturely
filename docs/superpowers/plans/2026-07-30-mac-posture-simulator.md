# Posturely Mac Simulator Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** Build and publicly publish Posturely, a privacy-first Mac posture simulator that uses a webcam or deterministic demo poses to drive three virtual diagnostic lights with the same portable posture, calibration, confidence, and timing engine intended for the Raspberry Pi appliance.

**Architecture:** Use a ports-and-adapters Python package. The pure `posturely.core` package accepts normalized landmark dataclasses and has no OpenCV or MediaPipe imports. Mac-only adapters own camera capture, pose inference, and the preview window. A deterministic demo adapter makes the full experience runnable without a camera and keeps CI headless. The application keeps frames only in memory, never opens a network listener, and performs no runtime cloud inference.

**Tech Stack:** Python 3.11, `uv`, MediaPipe Tasks Pose Landmarker, OpenCV, NumPy, pytest, Ruff, standard-library `argparse` and `json`, GitHub Actions.

**Global Constraints:**

- No frame, crop, thumbnail, landmark history, or posture-event history may be written.
- `src/posturely/core/` must never import `cv2`, `mediapipe`, or platform code.
- All alert timing must use an injected monotonic clock; tests must not sleep.
- Missing or low-confidence landmarks suppress alerts rather than count as bad posture.
- The three diagnostic categories remain independent.
- Generic thresholds work without calibration; calibration stores only median numeric features.
- Do not add an LLM, server, account, telemetry, database, custom training, or medical claims.
- Use MediaPipe for the Mac proof because its macOS arm64 wheel avoids the full TensorFlow dependency; retain the pose-adapter boundary so MoveNet remains swappable.
- The public repository must contain no personal video, captured frames, credentials, or local absolute paths.

## File Structure

```text
.
├── .github/workflows/ci.yml
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── scripts/fetch_pose_model.py
├── src/posturely/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── calibration.py
│   │   ├── evaluator.py
│   │   ├── features.py
│   │   ├── state_machine.py
│   │   └── types.py
│   └── adapters/
│       ├── __init__.py
│       ├── demo_pose.py
│       ├── mediapipe_pose.py
│       ├── opencv_camera.py
│       └── opencv_preview.py
├── tests/
│   ├── conftest.py
│   ├── test_calibration.py
│   ├── test_cli.py
│   ├── test_evaluator.py
│   ├── test_features.py
│   ├── test_privacy.py
│   └── test_state_machine.py
└── outputs/mac-simulator-handoff.md
```

## Task 1: Establish the Installable, Headless Project Skeleton

**Files:**

- Create: `pyproject.toml`
- Create: `src/posturely/__init__.py`
- Create: `src/posturely/__main__.py`
- Create: `src/posturely/core/__init__.py`
- Create: `src/posturely/adapters/__init__.py`
- Create: `tests/test_cli.py`
- Modify: `.gitignore`

**Steps:**

- [ ] Write a failing CLI smoke test that imports `posturely` and verifies `python -m posturely --help` exposes `--demo`, `--camera`, `--model`, `--mirror`, and `--no-preview`.

```python
def test_parser_exposes_runtime_modes() -> None:
    help_text = build_parser().format_help()
    for flag in ("--demo", "--camera", "--model", "--mirror", "--no-preview"):
        assert flag in help_text
```

- [ ] Run `UV_CACHE_DIR=work/uv-cache uv run --python 3.11 pytest tests/test_cli.py -q`.
- [ ] Confirm failure with `ModuleNotFoundError: No module named 'posturely'`.
- [ ] Add the minimal `pyproject.toml` with Python `>=3.11,<3.13`, runtime dependencies `mediapipe`, `numpy`, and `opencv-python`, and development dependencies `pytest` and `ruff`.
- [ ] Implement `build_parser()` and a `main()` seam without importing camera libraries at module import time.
- [ ] Add `.venv/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `assets/models/`, and local calibration files to `.gitignore`.
- [ ] Run the focused test and `uv run ruff check .`; expect both to pass.
- [ ] Commit: `chore: scaffold posturely simulator`

## Task 2: Define the Pure Landmark and Output Contracts

**Files:**

- Create: `src/posturely/core/types.py`
- Create: `tests/conftest.py`
- Create: `tests/test_features.py`

**Steps:**

- [ ] Add tests for immutable `Landmark`, `PoseFrame`, `PostureFeatures`, `IssueEvidence`, `DiagnosticColor`, `MonitoringState`, and `OutputState` types.
- [ ] Add synthetic neutral seated and standing fixtures using only the landmarks required by the spec: nose, ears, shoulders, elbows, and hips.
- [ ] Assert `PoseFrame.reliable(name, minimum=0.55)` is false for missing, low-visibility, or low-presence landmarks.
- [ ] Run `uv run pytest tests/test_features.py -q`; confirm import/type failures.
- [ ] Implement frozen dataclasses and enums. Make invalid normalized coordinates or confidence values raise `ValueError` with the offending field name.

```python
@dataclass(frozen=True, slots=True)
class Landmark:
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0
    presence: float = 1.0
```

- [ ] Rerun the focused tests; expect pass.
- [ ] Commit: `feat: define portable posture data contracts`

## Task 3: Extract Scale-Normalized Posture Features

**Files:**

- Create: `src/posturely/core/features.py`
- Modify: `tests/test_features.py`

**Steps:**

- [ ] Write tests proving translation and uniform scale do not materially change features.
- [ ] Write separate tests for:
  - head displacement and neck-angle proxy;
  - shoulder-line angle, apparent width, asymmetry, and shoulder-to-elbow relationship;
  - torso lean and shoulder-to-hip compression;
  - unavailable feature groups when required landmarks are unreliable.
- [ ] Run the feature tests and confirm failures for missing `extract_features`.
- [ ] Implement small vector helpers, midpoint/distance/angle helpers, and `extract_features(frame)`.
- [ ] Normalize by shoulder width with a guarded lower bound; never divide by an inferred or zero body scale.
- [ ] Return `None` per feature group when its evidence is insufficient instead of synthesizing landmarks.
- [ ] Rerun tests; expect pass.
- [ ] Commit: `feat: extract normalized posture geometry`

## Task 4: Evaluate Three Independent Posture Categories

**Files:**

- Create: `src/posturely/core/evaluator.py`
- Create: `tests/test_evaluator.py`

**Steps:**

- [ ] Write table-driven tests for neutral, forward head, shoulder imbalance/rounding proxy, torso slump, combined issues, and uncertain inputs.
- [ ] Assert one uncertain category does not suppress reliable evidence for the other two.
- [ ] Assert deliberate lateral head turning and discontinuous reach-like geometry produce uncertain evidence rather than an alert.
- [ ] Run the evaluator tests and confirm failures.
- [ ] Implement conservative `GenericThresholds`, optional baseline deltas, and `PostureEvaluator.evaluate(features, baseline=None)`.

```python
@dataclass(frozen=True, slots=True)
class Evidence:
    problematic: bool
    confident: bool
    magnitude: float
    reason: str
```

- [ ] Keep every threshold named and documented as an observable geometric proxy, not a medical standard.
- [ ] Rerun tests; expect pass.
- [ ] Commit: `feat: evaluate head shoulder and torso evidence`

## Task 5: Implement Exact Quiet-Until-Needed Timing

**Files:**

- Create: `src/posturely/core/state_machine.py`
- Create: `tests/test_state_machine.py`

**Steps:**

- [ ] Implement a `FakeClock` fixture and write boundary tests at 0, 4.999, 5, 14.999, and 15 seconds.
- [ ] Test independent issue timers, uncertainty reset/suppression, two-second correction recovery, and threshold hysteresis.
- [ ] Test monitoring states for healthy, absent/poor framing, and fault.
- [ ] Run the state-machine tests and confirm failures.
- [ ] Implement one `IssueTimer` per category and a `PostureStateMachine` with injected `Callable[[], float]`.

```python
state = machine.update(
    evidence=evidence,
    pose_present=True,
    fault=None,
)
```

- [ ] Ensure the transition outputs are off before five seconds, amber from five seconds, red from 15 seconds, and off after two corrected seconds.
- [ ] Rerun tests; expect pass with no real sleeping.
- [ ] Commit: `feat: add quiet posture alert state machine`

## Task 6: Add Optional Numeric Calibration

**Files:**

- Create: `src/posturely/core/calibration.py`
- Create: `tests/test_calibration.py`

**Steps:**

- [ ] Write tests for stable five-second capture, median aggregation, seated/standing separation, low-confidence rejection, unstable-pose rejection, baseline selection, JSON round-trip, and clearing all baselines.
- [ ] Assert serialized JSON contains only mode, numeric features, schema version, and timestamp—never landmarks or image-like byte fields.
- [ ] Run the calibration tests and confirm failures.
- [ ] Implement a `CalibrationSession` that receives already-extracted feature samples and an injected clock.
- [ ] Implement atomic numeric baseline persistence to an explicitly supplied path; default CLI behavior may use an ignored local file.
- [ ] Rerun tests; expect pass.
- [ ] Commit: `feat: calibrate numeric seated and standing baselines`

## Task 7: Build the Deterministic Full-System Demo

**Files:**

- Create: `src/posturely/adapters/demo_pose.py`
- Create: `src/posturely/app.py`
- Modify: `src/posturely/__main__.py`
- Modify: `tests/test_cli.py`

**Steps:**

- [ ] Write tests that a deterministic timeline produces neutral, head amber/red, shoulder amber/red, torso amber/red, recovery, absence, and return-to-monitoring states.
- [ ] Add a `--demo --no-preview --demo-seconds N` CLI path that runs without MediaPipe, OpenCV, a camera, or real-time sleeping when a test clock is supplied.
- [ ] Run the CLI tests and confirm failures.
- [ ] Implement synthetic landmark frames and a single `PostureApplication.process(frame, now)` orchestration path shared by demo and live modes.
- [ ] Print only current health/state transitions in headless mode; do not log landmarks or history.
- [ ] Rerun tests and a manual headless smoke test:

```bash
UV_CACHE_DIR=work/uv-cache uv run python -m posturely --demo --no-preview --demo-seconds 40
```

- [ ] Expect all three named diagnostic categories and monitoring transitions to appear.
- [ ] Commit: `feat: add deterministic posture simulator`

## Task 8: Add Live MediaPipe, Camera, and Preview Adapters

**Files:**

- Create: `scripts/fetch_pose_model.py`
- Create: `src/posturely/adapters/mediapipe_pose.py`
- Create: `src/posturely/adapters/opencv_camera.py`
- Create: `src/posturely/adapters/opencv_preview.py`
- Modify: `src/posturely/app.py`
- Modify: `src/posturely/__main__.py`

**Steps:**

- [ ] Write adapter contract tests with fake capture and fake pose-result objects before importing native libraries.
- [ ] Implement `OpenCVCamera` at 640×480, tolerate initial empty frames, expose explicit fault states, and always release in `finally`.
- [ ] Implement `MediaPipePoseAdapter` with `num_poses=1`, live/video timestamps that are monotonically increasing, and conversion into the pure `PoseFrame` contract.
- [ ] Implement a preview showing:
  - mirrored live frame when requested;
  - optional skeleton;
  - three labeled dots in head/shoulder/torso order;
  - monitoring indicator;
  - calibration status;
  - measured analysis FPS;
  - `c` calibrate, `x` clear calibration, `l` landmarks on/off, and `q` quit.
- [ ] Implement the model-fetch script with an official HTTPS source, fixed destination, basic size/hash validation, and no runtime auto-download.
- [ ] Run the complete headless suite; expect no camera access.
- [ ] Fetch the model once, then run the live simulator:

```bash
UV_CACHE_DIR=work/uv-cache uv run python scripts/fetch_pose_model.py
UV_CACHE_DIR=work/uv-cache uv run python -m posturely --camera 0 --model assets/models/pose_landmarker_lite.task
```

- [ ] Confirm macOS asks for Camera permission if needed and that quitting releases the camera.
- [ ] Commit: `feat: add private live Mac posture preview`

## Task 9: Enforce Privacy and Repository Quality

**Files:**

- Create: `tests/test_privacy.py`
- Create: `.github/workflows/ci.yml`
- Create: `LICENSE`
- Create: `README.md`

**Steps:**

- [ ] Write a static privacy test that scans product source for forbidden frame-persistence APIs such as `imwrite`, `VideoWriter`, `imencode`, `pickle.dump`, and application-owned HTTP listeners.
- [ ] Test that imports do not create files and that a headless demo changes no workspace files when calibration persistence is disabled.
- [ ] Run privacy tests first and confirm any forbidden test fixture is caught.
- [ ] Add an MIT license, plain-language privacy statement, non-medical disclaimer, setup instructions, keyboard controls, calibration explanation, architecture map, and limitations—especially monocular shoulder-rounding uncertainty.
- [ ] Add GitHub Actions for Python 3.11 headless `pytest` and `ruff`; do not attempt camera/model tests in CI.
- [ ] Run:

```bash
UV_CACHE_DIR=work/uv-cache uv run pytest -q
UV_CACHE_DIR=work/uv-cache uv run ruff check .
rg -n "TODO|FIXME|pass$|NotImplemented|imwrite|VideoWriter" src tests README.md
```

- [ ] Expect all tests and lint to pass and the placeholder/privacy scan to have no unexplained matches.
- [ ] Commit: `test: enforce privacy and document simulator`

## Task 10: Verify the Mac Proof and Publish the Public GitHub Repository

**Files:**

- Create: `outputs/mac-simulator-handoff.md`
- Modify: `docs/superpowers/specs/2026-07-30-posture-monitor-design.md`

**Steps:**

- [ ] Run the full automated suite from a clean environment.
- [ ] Run the deterministic demo and capture its textual transition summary.
- [ ] Run the live camera proof with Steve present:
  - neutral posture keeps all diagnostic dots off;
  - deliberate forward head independently reaches amber at five seconds and red at 15;
  - deliberate shoulder imbalance/rounding proxy drives only the middle dot when observable;
  - deliberate torso slump drives the bottom dot;
  - correction clears each light after two seconds;
  - absence/poor framing slow-pulses monitoring;
  - seated/standing frames remain stable;
  - analysis rate is at least five FPS;
  - no frame files are created.
- [ ] Record honest pass/fail findings in `outputs/mac-simulator-handoff.md`; do not represent unrun manual checks as passed.
- [ ] Update the design specification from “awaiting written-spec review” to the actual proof status.
- [ ] Confirm GitHub authentication and create a public repository named `posturely` without overwriting an existing remote:

```bash
gh auth status
gh repo view posturely
gh repo create posturely --public --source=. --remote=origin --description "Private, local posture feedback with quiet virtual lights"
git push -u origin main
```

- [ ] If `posturely` already exists, inspect its owner and remotes before choosing a non-conflicting name.
- [ ] Verify the repository page, default branch, README rendering, CI status, and absence of ignored/private assets.
- [ ] Commit before push: `docs: record Mac simulator verification`

## Final Self-Review

- [ ] Compare every implemented behavior against the approved design specification sections 6.1, 7, 8, 9, 10, and 13.1.
- [ ] Confirm the core package contains no platform imports.
- [ ] Confirm all public APIs use the same landmark, feature, evidence, and output types.
- [ ] Confirm every error path releases camera/model/window resources.
- [ ] Confirm no placeholder, unhandled expected exception, dead compatibility shim, or frame-writing code remains.
- [ ] Confirm the public Git history contains no models, frames, secrets, local calibration data, or personal paths.
- [ ] Invoke `superpowers:verification-before-completion` before reporting completion.
