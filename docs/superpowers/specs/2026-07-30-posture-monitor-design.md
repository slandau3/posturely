# Cost-First Standalone Posture Monitor Design

**Date:** 2026-07-30  
**Status:** Approved; Mac software proof implemented and undergoing live tuning  
**Owner:** Steve

## 1. Purpose

Build a small, contactless desk appliance that privately monitors Steve's posture while he works at a sitting or standing desk. It provides quiet, issue-specific visual feedback without requiring a laptop, wearable, cloud service, account, phone app, or saved history.

This is an awareness aid, not a medical or diagnostic device.

## 2. Goals

- Detect sustained forward-head or neck drift.
- Detect meaningful shoulder rounding or asymmetry when it is visually observable.
- Detect sustained whole-torso slump or excessive forward/side lean.
- Work while Steve alternates between sitting and standing.
- Run independently from USB-C power.
- Process images locally and discard every frame immediately.
- Identify the specific posture issue with a dedicated light.
- Remain visually quiet when posture is acceptable.
- Use the cheapest hardware that passes the acceptance tests.
- Be reproducible by a prototype builder from a complete software, CAD, and assembly handoff.

## 3. Non-goals

- Medical diagnosis, treatment recommendations, or claims about an anatomically perfect posture.
- Facial recognition, identity tracking, room surveillance, or remote viewing.
- Video or photo recording.
- Posture history, scores, streaks, reports, dashboards, or phone applications.
- Voice, sound, vibration, or screen-based alerts.
- Multi-person monitoring.
- Monitoring away from Steve's desk.
- Custom PCBs, injection molding, product certification, or production manufacturing for the first prototype.
- LLM inference or cloud-hosted machine learning.

## 4. Product Form

The prototype is a slim desk column approximately:

- 175–185 mm tall
- 60–70 mm wide
- 65–80 mm deep at the base

The enclosure has:

- A weighted, non-slip base.
- A wide-angle camera near the top, angled slightly upward.
- Three small vertically arranged RGB diagnostic dots.
- One separate, very dim white monitoring indicator near the base.
- One calibration button.
- A mechanical camera privacy shutter.
- Rear and bottom ventilation.
- A rear-bottom USB-C power opening.
- A removable rear or bottom panel for service.

The vertical diagnostic-dot mapping is:

1. Top: head and neck drift.
2. Middle: rounded or uneven shoulders.
3. Bottom: whole-torso slump or excessive lean.

The column sits roughly 600–900 mm from Steve and 20–35 degrees off-center. This position balances the partial side view needed for forward-head detection with the frontal information needed for shoulder alignment.

## 5. Cost-First Hardware

### 5.1 Preferred prototype bill of materials

| Part | Preferred choice | Target cost |
|---|---|---:|
| Compute | Raspberry Pi 5, 1 GB | $45 |
| Camera | Generic Linux-compatible UVC board camera, 720p or better, 90–120° field of view | $15–20 |
| Storage | 16–32 GB reputable microSD card | $7–10 |
| Power | Compatible USB-C power supply | $10–15 |
| Cooling | Small passive heatsink | $3–6 |
| Indicators | Three small addressable RGB LEDs and one dim white LED | $3–6 |
| Input | One momentary button | $1–3 |
| Interconnect | Perfboard, resistors, wire, connectors, and fasteners | $5–10 |
| Enclosure | PLA/PETG print, rubber feet, and inexpensive steel ballast | $15–35 |
| **Expected parts total** |  | **$104–150** |

Prices are approximate July 2026 US prices and exclude shipping and contractor labor.

### 5.2 Controlled fallbacks

The builder must bench-test the preferred parts before finalizing the enclosure. Upgrades are allowed only when a preferred part fails a stated acceptance criterion:

1. Replace the generic UVC module with a Raspberry Pi Camera Module 3 Wide if the generic camera has unreliable Linux support, poor low-light landmark confidence, or an unsuitable field of view.
2. Replace the 1 GB Pi with a 2 GB Pi only if measured memory pressure, sustained thermal throttling, or required inference performance cannot be resolved through software optimization.
3. Add a small fan only if the eight-hour thermal test fails with passive cooling.

The prototype will not use the Raspberry Pi AI Camera, a depth camera, LiDAR, thermal imaging, Wi-Fi CSI, UWB, or mmWave radar. These approaches cost more, provide poorer ready-made posture landmarks, or require substantially more custom R&D.

### 5.3 Cost controls

- Use a printed enclosure rather than machined or molded parts.
- Use perfboard or point-to-point assembly rather than a custom PCB.
- Use steel washers or plate offcuts as ballast.
- Use one power supply for the entire device.
- Do not add a display, speaker, microphone, battery, touch interface, or separate USB status lamp.
- Procure and bench-test exact components before freezing CAD dimensions.
- Prefer a single print with a removable service panel to minimize print time and rework.

## 6. Software Architecture

The software is a small local pipeline:

1. **Camera adapter**  
   Captures low-resolution frames from the selected camera. The target operating point is 640 × 480 at approximately five analyzed frames per second.

2. **Pose-landmark adapter**  
   Runs an ARM-compatible TensorFlow Lite pose model. MoveNet Lightning is the initial model because it is small and exposes the ears, shoulders, elbows, and hips needed by the posture features. The adapter boundary allows a later MediaPipe model without changing the rest of the system.

3. **Feature extractor**  
   Converts landmarks into scale-normalized features:
   - Head/neck: ear and nose displacement relative to the shoulder midpoint, plus a neck-angle proxy.
   - Shoulders: shoulder-line angle, apparent shoulder-width change, left/right asymmetry, and shoulder-to-elbow relationships.
   - Torso: shoulder-midpoint to hip-midpoint angle and vertical compression. If hip confidence is low, use a lower-confidence head/shoulder fallback rather than inventing a hip location.

4. **Posture evaluator**  
   Applies conservative geometric rules to the normalized features. Optional personalized baselines adjust thresholds for the installed camera angle and Steve's body proportions. A small classical classifier may be added later only if deterministic rules cannot meet the acceptance tests; an LLM is never part of the path.

5. **Temporal filter and state machine**  
   Smooths noisy measurements, requires sustained evidence, applies hysteresis, and drives the indicators.

6. **Hardware adapter**  
   Controls the diagnostic LEDs, monitoring LED, and calibration button without exposing GPIO details to posture logic.

7. **Supervisor**  
   Starts monitoring automatically at boot and restarts the service after a crash.

Each unit has one responsibility and a narrow interface so camera, model, and LED hardware can be replaced independently.

### 6.1 Mac-first proof mode

Before purchasing prototype hardware, the same posture engine runs locally on Steve's Mac with:

- A macOS camera adapter using the built-in camera or any temporarily connected webcam.
- A simple developer preview that can display pose landmarks while tuning.
- Three virtual diagnostic dots and one virtual monitoring indicator.
- The real calibration, timing, confidence, and seated/standing behavior.
- Frame writing disabled by default, exactly as it will be on the appliance.

The Mac proof validates the usefulness of the posture rules and interaction before money is spent. Platform-specific code remains behind the camera and hardware-adapter boundaries so the posture engine and tests transfer unchanged to Raspberry Pi.

The developer preview and landmark overlay are diagnostic tools only. They are not part of the final appliance experience and can be disabled entirely.

Hardware procurement begins only after the Mac proof demonstrates:

- Stable landmark extraction from sitting and standing positions.
- At least five analyzed frames per second on the Mac.
- Correct independent operation of all three virtual diagnostic dots.
- Optional calibration and generic thresholds both function.
- The forward-head and torso metrics are clearly useful.
- The shoulder metric is promising enough to continue or is explicitly narrowed to shoulder imbalance/elevation.
- No image or posture-history files are created.

## 7. Posture and Alert Behavior

### 7.1 Diagnostic timing

For each posture category independently:

- Acceptable or uncertain: diagnostic dot off.
- Continuous issue for 0–5 seconds: dot off.
- Continuous issue for 5–15 seconds: dot amber.
- Continuous issue for at least 15 seconds: dot red.
- Corrected continuously for two seconds: dot fades off.

Hysteresis prevents rapid flicker near a threshold. Temporary reaching, stretching, looking aside, and ordinary movement must not accumulate toward an alert when landmark geometry changes discontinuously.

### 7.2 Monitoring indicator

- Steady, very dim white: monitoring with adequate landmark confidence.
- Slow white pulse: waiting for one person, user out of frame, privacy shutter closed, or landmark confidence too low.
- Fast white pulse: camera, model, or software fault requiring attention.
- During startup: slow pulse until the monitoring loop is healthy.

The monitoring indicator must be dimmer than an amber diagnostic dot and should not draw attention in peripheral vision.

### 7.3 Sitting and standing

All core measurements are scale-normalized. The software infers a coarse seated or standing mode from stable landmark position and body scale, then selects a mode-specific optional baseline if one exists. Switching modes requires no button press.

If mode inference is uncertain, the evaluator uses conservative generic thresholds and suppresses low-confidence alerts.

## 8. Calibration

Calibration is optional.

- The device works immediately with conservative generic thresholds.
- Holding the button for two seconds begins a five-second capture.
- All three diagnostic dots pulse blue during capture.
- The user holds a comfortable upright posture.
- The system rejects the calibration if landmark confidence or pose stability is insufficient.
- A successful capture stores median normalized features for the detected seated or standing mode.
- The user may repeat calibration later in the other mode.
- Holding the button for ten seconds clears all personalized baselines and restores generic rules.

Calibration stores only numerical baseline features. It never stores source frames.

## 9. Privacy and Security

- Frames exist only in volatile memory for the duration of inference.
- No frame, crop, thumbnail, video, or pose history is written to storage.
- No account or cloud service is used.
- Wi-Fi and Bluetooth are disabled by default in the operating-system image.
- The monitoring service opens no network listener.
- Logs contain only software health and error codes, never landmarks or posture events.
- The physical shutter provides an unambiguous way to block the camera.
- The complete source and build configuration are included in the handoff for inspection.

## 10. Error Handling

- **No person or multiple people:** suppress posture output and slow-pulse the monitoring indicator.
- **Low light or occlusion:** suppress affected metrics; do not treat missing landmarks as bad posture.
- **Single-metric uncertainty:** leave only that diagnostic dot off while continuing reliable metrics.
- **Camera disconnect:** fast-pulse the monitoring indicator and retry camera initialization.
- **Model failure or process crash:** supervisor restarts the service; fast-pulse until healthy.
- **Thermal throttling:** reduce analyzed frame rate before allowing instability.
- **Filesystem becomes read-only or unavailable:** continue monitoring from memory when possible and fast-pulse the monitoring indicator.
- **Bad calibration capture:** flash the three diagnostic dots amber twice, discard the attempt, and retain the previous baseline.

## 11. Enclosure and CAD Handoff

The enclosure design must be parametric enough to accommodate the exact procured camera and minor Pi connector variations. The handoff includes:

- Editable CAD source.
- STEP when supported by the chosen CAD tool.
- STL or 3MF files ready for printing.
- Exploded assembly view.
- Exact fastener list.
- Camera optical-axis and field-of-view drawing.
- LED aperture and light-isolation details.
- Mechanical privacy-shutter geometry.
- Ventilation and heatsink clearance.
- Cable routing and strain relief.
- Suggested print orientation and settings.

The initial print uses an inexpensive dark matte PLA or PETG. Cosmetic finishing is out of scope. Internal light barriers prevent one diagnostic LED from illuminating another aperture.

## 12. Builder Handoff and Assembly

This is a one-off prototype job for an embedded-systems prototype builder or freelancer, not a production contract manufacturer.

The builder receives:

- Approved design specification.
- Bill of materials with acceptable substitutes.
- Source repository.
- Reproducible OS provisioning script and restorable SD-card image.
- CAD and print files.
- Wiring diagram.
- Assembly instructions.
- Calibration instructions.
- Acceptance-test checklist.

The builder must:

1. Confirm that the Mac-first proof gate has passed.
2. Procure the preferred parts.
3. Bench-test camera, model throughput, LEDs, button, and boot behavior before printing.
4. Report any failed acceptance criterion before purchasing an upgrade.
5. Confirm exact component dimensions and finalize the enclosure.
6. Print and assemble the unit.
7. Run the complete acceptance suite.
8. Ship the assembled unit, one restorable SD-card image, and any unused proprietary cable or fastener.

Target contractor labor is $100–300 once the design, code, and CAD are supplied. The expected delivered prototype total is approximately $220–450 before unusual shipping or rework.

## 13. Verification

### 13.1 Software tests

- Unit tests for landmark normalization and all posture features.
- Unit tests for seated/standing baseline selection.
- State-machine tests for off, amber, red, recovery, uncertainty, and calibration behavior.
- Tests proving missing or low-confidence landmarks cannot create alerts.
- Tests proving no image-writing code path exists.
- Supervisor restart test.

Development may use short, consented test clips. Test media is excluded from the product image and deliverable repository.

### 13.2 Hardware tests

- Cold boot to healthy monitoring in no more than 60 seconds.
- Eight continuous operating hours without crash or unrecovered camera failure.
- No sustained thermal throttling at the target analysis rate.
- Button, privacy shutter, every LED color, and every indicator state verified.
- Power interruption and automatic recovery verified.
- Network scan confirms no listener and disabled wireless radios.

### 13.3 Posture acceptance tests

At the intended desk position and after optional calibration:

- Detect obvious sustained forward-head posture in at least 9 of 10 deliberate 20-second trials.
- Detect obvious sustained whole-torso slump in at least 9 of 10 deliberate 20-second trials.
- Demonstrate whether the shoulder metric reliably distinguishes deliberate inward rounding and deliberate one-sided shoulder elevation from neutral posture.
- Produce fewer than one false red alert per hour during two hours of ordinary mixed desk work.
- Switch between seated and standing operation without manual mode selection.
- Produce no alert while the user is absent, partially out of frame, stretching, or performing brief reaches.

If the shoulder metric cannot meet a useful reliability threshold, retain the middle light but redefine it as **shoulder imbalance/elevation**, which is more observable from a single camera than clinical shoulder rounding. This change requires Steve's approval before final delivery.

## 14. Principal Risks and Mitigations

### Shoulder rounding from one camera

Rounded shoulders are the hardest target because protraction is a three-dimensional change. The off-center view, elbows, apparent shoulder width, and personalized baseline improve observability. The acceptance test prevents shipping a misleading shoulder indicator.

### Cheap-camera inconsistency

Generic UVC modules vary in lens, exposure, and Linux behavior. Procure from a returnable source, bench-test before enclosure work, and use the Camera Module 3 Wide only if needed.

### False-alert fatigue

Conservative thresholds, five-second amber delay, 15-second red delay, hysteresis, and confidence gating prioritize trust over detecting every small deviation.

### Prototype labor exceeding part savings

Avoid exotic sensors, custom PCBs, custom model training, mobile applications, production finishes, and unsupported single-board computers. Saving $10 on hardware is not worthwhile if it creates hours of integration work.
