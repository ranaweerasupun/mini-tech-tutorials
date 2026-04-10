# Raspberry Pi Camera Tutorial

[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/Content-CC--BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

A practical, open-source guide to working with the Raspberry Pi Camera using Python and the **Picamera2** library. We start from physical connection and work through to real projects — time-lapses, motion detection, numpy frame processing, and video recording.

---

## What You'll Learn

How to connect and verify a Pi Camera, control it from Python, understand the Picamera2 architecture well enough that things stop being mysterious, and build a handful of genuinely useful projects.

---

## Tutorial Structure

Work through the documents in order if you're starting fresh. If you have some camera experience already, jump to whatever section is relevant.

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [Hardware Setup](docs/01-hardware-setup.md) | Connecting the camera, ribbon cable handling, enabling the interface, verifying detection |
| 02 | [Python Camera Basics](docs/02-python-camera-basics.md) | Picamera2 installation, first script, camera controls, numpy arrays |
| 03 | [Picamera2 Architecture](docs/03-picamera2-architecture.md) | The full library architecture — layers, streams, encoders, previews |
| 04 | [Practical Projects](docs/04-projects.md) | Time-lapse, button-triggered capture, motion detection, video recording |
| 05 | [Troubleshooting](docs/05-troubleshooting.md) | Common errors, fixes, diagnostic commands |

---

## Quick Start

If you just want a photo captured as fast as possible:

**Step 1 — Connect the camera** (see [Hardware Setup](docs/01-hardware-setup.md))

**Step 2 — Install Picamera2:**

```bash
sudo apt install python3-picamera2 python3-numpy python3-pil
```

**Step 3 — Run your first capture:**

```python
from picamera2 import Picamera2
import time

picam2 = Picamera2()
picam2.start()
time.sleep(2)               # Let auto-exposure settle
picam2.capture_file("hello.jpg")
picam2.stop()
print("Done! Check hello.jpg")
```

---

## Code Samples

All standalone, ready-to-run scripts live in the [`code/`](code/) folder:

- [`first_camera.py`](code/first_camera.py) — Minimal capture script
- [`interactive_camera.py`](code/interactive_camera.py) — Press Enter to shoot, type quit to exit
- [`camera_settings.py`](code/camera_settings.py) — Brightness, contrast, saturation demos
- [`capture_array.py`](code/capture_array.py) — Capture into a numpy array for processing
- [`timelapse.py`](code/timelapse.py) — Automated time-lapse with configurable interval
- [`button_trigger.py`](code/button_trigger.py) — GPIO button-triggered capture
- [`motion_detect.py`](code/motion_detect.py) — Frame-differencing motion detector
- [`video_record.py`](code/video_record.py) — H.264 video recording with start/stop

---

## Requirements

- Raspberry Pi (any model with a CSI camera connector — Pi 3, 4, 5, or Zero 2 W)
- Raspberry Pi Camera Module (v1, v2, v3, or HQ Camera)
- Raspberry Pi OS **Bookworm** (recommended) or Bullseye
- Python 3.8 or newer

---

## Tested On

| Hardware | Camera | OS |
|----------|--------|-----|
| Raspberry Pi 4 Model B | Camera Module 3 | Raspberry Pi OS Bookworm (64-bit) |
| Raspberry Pi Zero 2 W | Camera Module v2 | Raspberry Pi OS Bullseye (32-bit) |

---

## Contributing

Contributions are welcome. If you spot an error, want to add a project, or have a better explanation for something, open an issue or submit a pull request.

---

## License

**Code** (all `.py` files) — [MIT License](LICENSE)
**Tutorial content** (all `.md` files and written documentation) — [CC BY-NC 4.0](LICENSE)

Code is free to use in your own projects without restriction.
The written tutorials may be shared and adapted for non-commercial purposes with attribution. They may not be repackaged or sold.

© 2025 [Supun Akalanka Sriyananda]
