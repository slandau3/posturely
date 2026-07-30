# Posturely Builder and Acceptance Guide

## Before printing

1. Install Raspberry Pi OS Lite 64-bit and disable Wi-Fi/Bluetooth unless
   needed temporarily for provisioning.
2. Install Posturely under `/opt/posturely`, fetch the local pose model, and
   run the headless synthetic suite.
3. Bench-test the exact camera at 640×480, the three RGB LEDs, monitoring LED,
   calibration button, and service restart.
4. Measure the camera PCB/lens, LED bodies, button, Pi/heatsink, connectors,
   ballast, and fasteners. Enter those values in `posturely-column.scad`.
5. Export a draft STL, inspect wall thickness/cutouts, and print only after the
   measured model clears all components and cables.

## Assembly

- Print the body and rear panel in dark matte PETG or PLA.
- Install internal light barriers before the LED board.
- Add heat-set inserts or captive nuts for the rear panel.
- Bond or mechanically retain steel ballast in the sealed base pocket.
- Fit rubber feet, camera, shutter, LEDs, button, Pi/heatsink, and strain relief.
- Wire according to `wiring.md`; verify resistance before applying power.
- Install `deploy/posturely.service`, create `/var/lib/posturely`, and enable
  the service only after bench testing.

## Acceptance checklist

- [ ] Cold boot reaches healthy monitoring within 60 seconds.
- [ ] Camera inference sustains at least five analyzed FPS.
- [ ] Every LED shows the intended off, amber, red, blue, and monitoring state.
- [ ] Calibration button captures and clears numeric baselines correctly.
- [ ] Seated and standing synthetic tests pass on the Pi.
- [ ] Eight-hour continuous run has no crash or unrecovered camera failure.
- [ ] Thermal test shows no sustained throttling; add a fan only after failure.
- [ ] Privacy shutter fully blocks pose detection and produces waiting state.
- [ ] Network scan finds no listener; wireless radios are disabled for delivery.
- [ ] Power recovery restarts monitoring without keyboard or display.
- [ ] Camera and LED apertures do not leak light into neighboring indicators.
- [ ] Calibration file contains numbers only; no images or landmark history exist.

Record actual results. An unchecked physical item remains unverified and must
not be represented as passed.
