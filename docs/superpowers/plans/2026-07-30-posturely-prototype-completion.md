# Posturely Prototype Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete and verify the instrumented Posturely software simulator before adding a tested Raspberry Pi LED boundary and builder-ready hardware package.

**Architecture:** Extend the pure posture core with immutable analysis/progress contracts, calibrated evaluation, and stable desk-mode estimation. `PostureApplication` remains the single orchestration path for synthetic and live frames; OpenCV only renders its analysis snapshot. After the software-simulation gate passes, add a lazily imported Pi output adapter and documentation/CAD artifacts without changing posture logic.

**Tech Stack:** Python 3.11, standard-library dataclasses/JSON/argparse, MediaPipe Tasks, OpenCV, NumPy, pytest, Ruff, OpenSCAD source, GitHub Actions.

## Global Constraints

- Complete and verify the camera-free software simulation before Pi/CAD work.
- Do not require Steve to perform another physical posture session.
- Never persist frames, landmarks, analysis snapshots, scores, or posture history.
- Calibration may persist only schema-versioned numeric feature medians.
- `src/posturely/core/` must not import OpenCV, MediaPipe, GPIO, or platform code.
- Generic thresholds must work with no calibration.
- The three diagnostic categories and timers remain independent.
- The state machine remains the sole timing authority.
- Native libraries and hardware dependencies remain lazy imports.
- No LLM, cloud inference, account, server, database, telemetry, custom training, or medical claims.

---

## File Structure

### Software-simulation gate

- Create `src/posturely/core/analysis.py`: immutable scores, progress, mode, and snapshot contracts.
- Create `src/posturely/core/mode.py`: stable seated/standing/generic estimation.
- Create `src/posturely/calibration_runtime.py`: calibration capture, persistence, confirmation, and status orchestration.
- Modify `src/posturely/core/state_machine.py`: observable timer progress.
- Modify `src/posturely/core/evaluator.py`: optional baseline-relative scoring.
- Modify `src/posturely/app.py`: shared snapshot-producing orchestration.
- Modify `src/posturely/adapters/opencv_preview.py`: developer overlay and controls.
- Modify `src/posturely/live.py`: calibration, controls, rolling FPS, and snapshot wiring.
- Modify `src/posturely/demo_ui.py`: fully instrumented automatic simulation.
- Modify `src/posturely/__main__.py`: calibration path and developer-overlay options.
- Add or modify focused tests under `tests/`.

### Post-simulation hardware package

- Create `src/posturely/outputs.py`: platform-neutral output protocol.
- Create `src/posturely/adapters/pi_leds.py`: lazy GPIO LED implementation.
- Create `deploy/posturely.service`: systemd template.
- Create `hardware/posturely-column.scad`: parametric slim-column concept.
- Create `hardware/wiring.md`: GPIO and electrical guidance.
- Create `hardware/bom.md`: costed prototype parts and fallbacks.
- Create `hardware/assembly.md`: provisioning, assembly, and acceptance checklist.
- Update `README.md` and `outputs/mac-simulator-handoff.md`.

---

### Task 1: Immutable Analysis and Timer Progress

**Files:**

- Create: `src/posturely/core/analysis.py`
- Modify: `src/posturely/core/state_machine.py`
- Modify: `tests/test_state_machine.py`
- Create: `tests/test_analysis.py`

**Interfaces:**

- Produces `IssueProgress(problematic_seconds, corrected_seconds, next_transition_seconds)`.
- Produces `DiagnosticProgress(head, shoulders, torso)`.
- Produces immutable `CalibrationStatus` and `AnalysisSnapshot` view contracts
  without importing runtime controllers into the core.
- `PostureStateMachine.progress() -> DiagnosticProgress`.
- Later tasks consume these contracts without inspecting private timer state.

- [ ] **Step 1: Write failing boundary tests**

Add assertions at neutral, 4.0, 5.0, 14.0, 15.0, recovery, and uncertainty:

```python
progress = machine.progress().head
assert progress.problematic_seconds == pytest.approx(4.0)
assert progress.next_transition_seconds == pytest.approx(1.0)
```

Assert a paused tracking interval is excluded from `problematic_seconds`.

- [ ] **Step 2: Verify red**

Run:

```bash
.venv/bin/pytest tests/test_analysis.py tests/test_state_machine.py -q
```

Expected: import/API failures for the missing analysis contracts and
`PostureStateMachine.progress`.

- [ ] **Step 3: Implement minimal progress contracts**

Add frozen, slotted dataclasses. Make `_IssueTimer.progress(now)` derive values
from existing timestamps without mutating them. Return `None` for a transition
that is not currently counting.

- [ ] **Step 4: Verify green**

Run the same focused command and expect all selected tests to pass.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/core/analysis.py src/posturely/core/state_machine.py tests/test_analysis.py tests/test_state_machine.py
git commit -m "feat: expose posture timer progress"
```

### Task 2: Baseline-Relative Evaluator Scores

**Files:**

- Modify: `src/posturely/core/evaluator.py`
- Modify: `tests/test_evaluator.py`

**Interfaces:**

- `PostureEvaluator.evaluate(features, baseline: Baseline | None = None) -> PostureEvidence`.
- `Evidence.magnitude` remains the normalized score consumed by the overlay.

- [ ] **Step 1: Write failing calibrated-evaluator tests**

Cover:

```python
baseline = Baseline(
    mode=CalibrationMode.SEATED,
    features={
        "head.horizontal_offset": 0.20,
        "head.neck_angle_degrees": 10.0,
        "shoulders.line_angle_degrees": 3.0,
        "shoulders.asymmetry": 0.05,
        "shoulders.elbow_inset": 0.05,
        "shoulders.width_to_torso": 0.70,
        "torso.lean_degrees": 5.0,
        "torso.compression": 1.60,
    },
    captured_at=1.0,
)
```

Assert the baseline itself scores below `1.0`, meaningful deltas trigger only
their category, missing optional width data remains valid, and no-baseline
behavior exactly matches current generic evaluation.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_evaluator.py -q`; expect signature/behavior
failures because `baseline` is not accepted.

- [ ] **Step 3: Implement conservative named deltas**

Add a frozen `CalibrationDeltas` with:

- head offset `0.20`, head angle `12°`;
- shoulder line `6°`, asymmetry `0.10`, elbow inset increase `0.15`,
  width-ratio decrease `0.12`;
- torso lean `8°`, compression decrease `0.25`.

Normalize absolute directional deltas, preserve discontinuity checks, and use
generic evaluation whenever `baseline is None`.

- [ ] **Step 4: Verify green and regression**

Run:

```bash
.venv/bin/pytest tests/test_evaluator.py tests/test_demo.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/posturely/core/evaluator.py tests/test_evaluator.py
git commit -m "feat: evaluate calibrated posture deltas"
```

### Task 3: Stable Desk-Mode Estimation

**Files:**

- Create: `src/posturely/core/mode.py`
- Create: `tests/test_mode.py`

**Interfaces:**

- Produces `DeskMode.GENERIC`, `DeskMode.SEATED`, and `DeskMode.STANDING`.
- `ModeEstimator.update(frame: PoseFrame | None) -> DeskMode`.
- `ModeEstimator.override(mode: DeskMode | None) -> None`.

- [ ] **Step 1: Write failing mode tests**

Use synthetic frames to prove:

- fewer than five reliable frames stays `generic`;
- five consistent high-body frames yields `standing`;
- five consistent lower-body frames yields `seated`;
- mixed votes stay `generic`;
- absent/unreliable frames do not invent a mode;
- explicit seated/standing override wins and can be cleared.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_mode.py -q`; expect missing-module failure.

- [ ] **Step 3: Implement bounded voting**

Use only reliable shoulder/hip midpoint `y` values. Keep a maximum of five
votes, require four matching votes, classify body midpoint `< 0.48` as
standing and `>= 0.48` as seated, and expose no sample history.

- [ ] **Step 4: Verify green**

Run `.venv/bin/pytest tests/test_mode.py -q`.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/core/mode.py tests/test_mode.py
git commit -m "feat: infer stable seated and standing modes"
```

### Task 4: Runtime Calibration Controller

**Files:**

- Create: `src/posturely/calibration_runtime.py`
- Modify: `src/posturely/core/calibration.py`
- Create: `tests/test_calibration_runtime.py`
- Modify: `tests/test_calibration.py`

**Interfaces:**

- Produces `CalibrationPhase.IDLE`, `NEEDS_MODE`, `CAPTURING`, `SUCCEEDED`,
  `FAILED`, and `CONFIRM_CLEAR`.
- Uses core `CalibrationStatus(phase, mode, progress, message)`.
- `CalibrationController.start(mode, now)`, `choose_mode(mode, now)`,
  `update(features, now)`, `request_clear(now)`, and `active_baseline(mode)`.

- [ ] **Step 1: Write failing controller tests**

Prove:

- `start(generic)` requests mode rather than guessing;
- choosing seated/standing begins capture;
- five seconds of complete samples saves one numeric baseline;
- incomplete and unstable captures fail without replacing an old baseline;
- first clear request only asks for confirmation;
- a second request within three seconds clears and saves;
- expired confirmation preserves data;
- invalid existing JSON yields a warning and generic operation.

- [ ] **Step 2: Verify red**

Run:

```bash
.venv/bin/pytest tests/test_calibration_runtime.py tests/test_calibration.py -q
```

Expected: missing controller/status APIs.

- [ ] **Step 3: Add the minimal controller**

Inject clock and explicit `Path`. Load a store when valid, preserve the load
error as status when invalid, and use the existing atomic `BaselineStore.save`.
Add only safe read helpers such as `BaselineStore.modes()`.

- [ ] **Step 4: Verify green**

Run the focused command and expect all tests to pass.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/calibration_runtime.py src/posturely/core/calibration.py tests/test_calibration_runtime.py tests/test_calibration.py
git commit -m "feat: connect safe numeric calibration"
```

### Task 5: Shared Analysis Snapshot Application

**Files:**

- Modify: `src/posturely/core/analysis.py`
- Modify: `src/posturely/app.py`
- Create: `tests/test_app.py`
- Modify: `tests/test_demo.py`

**Interfaces:**

- Completes the core `AnalysisSnapshot(state, features, evidence, progress,
  mode, baseline_mode, calibration)` contract.
- `PostureApplication.process(...) -> OutputState` stays backward compatible.
- `PostureApplication.snapshot` exposes the latest snapshot.
- `PostureApplication.handle_command(key, now)` handles calibration/mode
  commands without UI dependencies.

- [ ] **Step 1: Write failing application tests**

Assert one synthetic frame produces matching features, evidence, state,
progress, and mode in one snapshot. Assert a selected baseline reaches the
evaluator. Assert `c`, `1`, `2`, and double-`x` commands update calibration
status. Assert snapshots are immutable.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_app.py tests/test_demo.py -q`; expect missing
snapshot/application APIs.

- [ ] **Step 3: Implement single-path orchestration**

Extract features once, update mode once, select the matching baseline, evaluate,
advance the state machine, update calibration, and publish one snapshot.
Retain transition-only console output and the existing `OutputState` return.

- [ ] **Step 4: Verify green**

Run:

```bash
.venv/bin/pytest tests/test_app.py tests/test_demo.py tests/test_calibration_runtime.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/posturely/core/analysis.py src/posturely/app.py tests/test_app.py tests/test_demo.py
git commit -m "feat: publish complete posture analysis snapshots"
```

### Task 6: Instrumented OpenCV Preview

**Files:**

- Modify: `src/posturely/adapters/opencv_preview.py`
- Modify: `tests/test_live_adapters.py`

**Interfaces:**

- Add pure `diagnostic_rows(snapshot) -> list[DiagnosticRow]`.
- `OpenCVPreview.render(..., snapshot, show_landmarks, show_details) -> int`.

- [ ] **Step 1: Write failing pure-layout tests**

For healthy, uncertain, amber, and red snapshots, assert rows expose exact
labels, scores, statuses, reasons, and countdown text. Assert rendering writes
mode/calibration/monitoring/FPS copy and respects both visibility toggles.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_live_adapters.py -q`; expect missing layout
and render-argument failures.

- [ ] **Step 3: Implement compact overlay**

Keep colors and dots unchanged. Add progress bars and developer text on a dark
translucent side panel. Keep all layout computation pure; OpenCV calls only
paint the resulting rows. Controls copy: `c calibrate · 1 seated · 2 standing
· x clear · l landmarks · d details · q quit`.

- [ ] **Step 4: Verify green**

Run the focused test and `.venv/bin/ruff check src/posturely/adapters/opencv_preview.py`.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/adapters/opencv_preview.py tests/test_live_adapters.py
git commit -m "feat: explain live posture scores and countdowns"
```

### Task 7: Live Controls, Persistence, and Rolling FPS

**Files:**

- Modify: `src/posturely/__main__.py`
- Modify: `src/posturely/live.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_live_runner.py`

**Interfaces:**

- CLI adds `--calibration-file`, `--no-details`, and `--no-landmarks`.
- `RollingFps.update(now) -> float` keeps at most 30 timestamps.
- Live keys delegate calibration to `PostureApplication`.

- [ ] **Step 1: Write failing CLI/live tests**

Assert:

- the new options parse and dispatch;
- the default calibration path is `.posturely-calibration.json`;
- several frames produce nonzero rolling FPS;
- `l` and `d` toggle preview flags;
- calibration keys are delivered to the application;
- q/Escape still releases every resource;
- headless mode never constructs a preview.

- [ ] **Step 2: Verify red**

Run:

```bash
.venv/bin/pytest tests/test_cli.py tests/test_live_runner.py -q
```

- [ ] **Step 3: Implement live wiring**

Inject an application factory for tests. Create calibration only for live mode,
update rolling FPS on each analyzed frame, pass the current snapshot to the
preview, and process key commands after rendering.

- [ ] **Step 4: Verify green**

Run the focused tests and all privacy tests.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/__main__.py src/posturely/live.py tests/test_cli.py tests/test_live_runner.py
git commit -m "feat: wire live calibration controls and fps"
```

### Task 8: Polished Automatic Software Simulation

**Files:**

- Modify: `src/posturely/demo_ui.py`
- Modify: `src/posturely/adapters/demo_pose.py`
- Modify: `tests/test_demo_ui.py`
- Modify: `tests/test_demo.py`
- Modify: `README.md`

**Interfaces:**

- The demo uses the same `AnalysisSnapshot` and preview interface as live mode.
- The synthetic timeline includes neutral, each issue, correction, absence,
  seated framing, and standing framing.

- [ ] **Step 1: Write failing end-to-end simulation tests**

Record preview snapshots and assert:

- every category passes through off, amber, red, and recovery;
- countdown values decrease at exact simulated times;
- both seated and standing labels stabilize;
- absence enters waiting and returns healthy;
- every rendered score equals the corresponding evidence magnitude;
- no camera factory, calibration file, MediaPipe, or real sleeping is used.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_demo.py tests/test_demo_ui.py -q`; expect
snapshot/render-contract failures.

- [ ] **Step 3: Implement the completed simulator**

Use in-memory calibration-disabled application wiring. Add a clear title and
phase label to the generated canvas. Keep default playback at 10x and allow q
or Escape to stop.

- [ ] **Step 4: Software-simulation acceptance gate**

Run:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/python -m posturely --demo --no-preview --demo-seconds 70
```

Then open `.venv/bin/python -m posturely --demo` and confirm the automatic
window completes without a camera. Do not begin Task 9 until every automated
command exits zero and the visual sequence is readable.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/demo_ui.py src/posturely/adapters/demo_pose.py tests/test_demo_ui.py tests/test_demo.py README.md
git commit -m "feat: complete instrumented posture simulator"
```

### Task 9: Portable Output Protocol and Pi LED Adapter

**Files:**

- Create: `src/posturely/outputs.py`
- Create: `src/posturely/adapters/pi_leds.py`
- Create: `tests/test_outputs.py`

**Interfaces:**

- `PostureOutput.apply(snapshot: AnalysisSnapshot, now: float) -> None`.
- `PiLedOutput` accepts injected LED/button factories and lazily imports GPIO.

- [ ] **Step 1: Write failing mapping/cleanup tests**

Assert RGB mappings for off/amber/red, steady/slow/fast monitoring patterns,
blue calibration capture, button command callbacks, all-off cleanup, and no
GPIO import under injected factories.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_outputs.py -q`; expect missing modules.

- [ ] **Step 3: Implement minimal adapter**

Keep posture logic out of the adapter. Use explicit BCM pin constants, inject
factories for tests, and raise a concise installation error only when the real
Pi adapter is constructed without its GPIO dependency.

- [ ] **Step 4: Verify green**

Run focused tests, privacy tests, and Ruff.

- [ ] **Step 5: Commit**

```bash
git add src/posturely/outputs.py src/posturely/adapters/pi_leds.py tests/test_outputs.py
git commit -m "feat: add raspberry pi posture light adapter"
```

### Task 10: Builder Package and Parametric Slim Column

**Files:**

- Create: `deploy/posturely.service`
- Create: `hardware/posturely-column.scad`
- Create: `hardware/wiring.md`
- Create: `hardware/bom.md`
- Create: `hardware/assembly.md`
- Create: `tests/test_hardware_handoff.py`

**Interfaces:**

- OpenSCAD top-level dimensions default to 180 × 65 × 72 mm.
- Documentation uses the same pins and commands as `PiLedOutput`.

- [ ] **Step 1: Write failing handoff consistency tests**

Parse the text artifacts and assert:

- every configured BCM pin appears in the wiring guide;
- the service command uses installed Posturely CLI options;
- required adjustable CAD parameters and cutout modules exist;
- BOM totals remain within the approved parts target;
- acceptance checklist includes boot, eight-hour, thermal, camera, LED,
  calibration, network, and power-recovery checks.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_hardware_handoff.py -q`; expect missing files.

- [ ] **Step 3: Create the truthful builder package**

Add a parametric two-piece enclosure concept with camera, three diagnostic
dots, monitoring dot, button, ventilation, USB-C, ballast, mounting, internal
light barriers, and removable rear panel. Document that exact purchased-part
measurements must be applied before STL export.

- [ ] **Step 4: Verify green**

Run the focused test. If `openscad` exists, run:

```bash
openscad -o work/posturely-column.stl hardware/posturely-column.scad
```

If unavailable, report it as unrendered and rely on syntax/structure checks;
do not claim a verified STL.

- [ ] **Step 5: Commit**

```bash
git add deploy hardware tests/test_hardware_handoff.py
git commit -m "docs: add posturely builder and enclosure package"
```

### Task 11: Documentation, Privacy, and Public Verification

**Files:**

- Modify: `README.md`
- Modify: `outputs/mac-simulator-handoff.md`
- Modify: `docs/superpowers/specs/2026-07-30-posturely-prototype-completion-design.md`
- Modify: `tests/test_privacy.py`

**Interfaces:**

- README commands must match the CLI and private launcher.
- Handoff distinguishes automated proof, camera-free manual proof, and future
  physical desk/hardware checks.

- [ ] **Step 1: Add failing documentation/privacy checks**

Assert calibration and Pi additions do not introduce frame writing, network
listeners, landmark persistence, or platform imports in the core. Assert README
contains simulator controls, live private command, calibration privacy, Pi
status, and non-medical limitations.

- [ ] **Step 2: Verify red**

Run `.venv/bin/pytest tests/test_privacy.py -q`; expect missing documentation
or new compliance assertions to fail.

- [ ] **Step 3: Update documentation honestly**

Record exact automated results and camera-free simulator behavior. Keep the
physical Pi and user-specific classifier acceptance checks explicitly unrun.
Mark the completion design implemented only after the commands below pass.

- [ ] **Step 4: Final local verification**

Run fresh:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
git diff --check
rg -n "TODO|FIXME|NotImplemented|pass$|imwrite|VideoWriter|VideoCapture.*write" src tests README.md hardware deploy
.venv/bin/python -m posturely --demo --no-preview --demo-seconds 70
git status --short
```

Explain every intentional `rg` match. Confirm no generated model, calibration
file, image, video, or STL is staged.

- [ ] **Step 5: Camera-free visual smoke**

Run `.venv/bin/python -m posturely --demo`; confirm all three lights, scores,
countdowns, both desk modes, absence, and recovery are visible. No camera test
is required.

- [ ] **Step 6: Commit, push, and verify CI**

```bash
git add README.md outputs/mac-simulator-handoff.md docs/superpowers/specs/2026-07-30-posturely-prototype-completion-design.md tests/test_privacy.py
git commit -m "docs: complete posturely prototype handoff"
git push origin main
gh run list --repo slandau3/posturely --branch main --limit 1
gh run watch RUN_ID --repo slandau3/posturely --exit-status
```

Expected: public GitHub CI completes successfully for the pushed commit.

## Final Self-Review

- [ ] Every production function added in this phase has a test that was observed
  failing first.
- [ ] The software-simulation gate passed before Pi/CAD work began.
- [ ] The app, demo, and Pi adapter consume the same snapshot/output contracts.
- [ ] Calibration changes evaluator behavior and stores only numeric medians.
- [ ] Generic mode works when calibration/mode inference is unavailable.
- [ ] Debug details do not alter the quiet three-light product behavior.
- [ ] All camera/model/window/GPIO resources close on exit and faults.
- [ ] No public file contains personal images, landmarks, secrets, calibration,
  local absolute paths, or unsupported claims.
- [ ] Final completion claims quote fresh test, lint, smoke, and CI evidence.
