# Posturely Cost-First Prototype BOM

Pricing checked 2026-07-30 in USD, before tax and shipping. Buy the camera
before freezing its CAD parameters.

| Part | Preferred prototype choice | Budget |
|---|---|---:|
| Compute | Raspberry Pi 5, 1 GB | $45 |
| Camera | Returnable Linux-compatible 720p+ wide-angle UVC board camera | $15–20 |
| Storage | Reputable 32 GB microSD | $8 |
| Power | Compatible 5 V / 5 A USB-C supply | $12 |
| Cooling | Passive Pi 5 heatsink | $5 |
| Indicators | 3 common-cathode RGB LEDs, 1 white LED, resistors | $4 |
| Input | Normally-open momentary button | $2 |
| Interconnect | Perfboard, wire, headers, fasteners, feet | $6 |
| Enclosure | Dark PLA/PETG plus steel washer ballast | $15–30 |
| **Expected parts total** |  | **$112–$132** |

Raspberry Pi announced the 1 GB Pi 5 at $45 in December 2025 and reported that
1 GB pricing was protected during its February 2026 memory increases:
https://www.raspberrypi.com/news/1gb-raspberry-pi-5-now-available-at-45-and-memory-driven-price-rises/

Camera fallback: use the official Camera Module 3 Wide only if the returnable
UVC module fails Linux, field-of-view, low-light, or landmark-confidence bench
tests. The official wide module has a 120° diagonal field of view and a $35
list price:
https://www.raspberrypi.com/products/camera-module-3/

Do not buy an AI Camera, depth camera, LiDAR, custom PCB, display, battery,
speaker, or active fan before a measured acceptance failure requires it.
