# Posturely Prototype Wiring

This pin map is the tested contract in `PiLedOutput`. Use common-cathode RGB
LEDs. Put one 220–330 Ω resistor between every color pin and LED leg; connect
each common cathode to ground. Never power an LED directly from a GPIO pin.

| Function | Raspberry Pi BCM pins |
|---|---|
| Head RGB | red BCM 17, green BCM 27, blue BCM 22 |
| Shoulder RGB | red BCM 5, green BCM 6, blue BCM 13 |
| Torso RGB | red BCM 19, green BCM 26, blue BCM 21 |
| Dim white monitoring LED | PWM signal BCM 20 through 330 Ω |
| Calibration button | input BCM 16 to a normally-open button; other side to GND |

The current software adapter drives the four lights. BCM 16 is reserved for
the physical button; connect its event to the same `c`/clear command boundary
during bench integration. Keep LED grounds, button ground, and Pi ground
common. Add labeled disconnects so the service panel can be removed.

Bench-check every channel at low duty cycle before installation. If the chosen
RGB package is common-anode, do not simply reverse it: change the adapter's
active-high configuration and re-run the light tests.
