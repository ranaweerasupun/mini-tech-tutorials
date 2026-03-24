# 📷 Raspberry Pi Camera Tutorial

A comprehensive, open-source guide to working with the Raspberry Pi Camera using Python and the **Picamera2** library. This tutorial is designed for all skill levels — whether you're wiring up your first camera module or building a computer vision pipeline, there's something here for you.

---

## What You'll Learn

By the end of this tutorial, you will be able to connect and verify a Pi Camera, control it from Python, understand the full Picamera2 library architecture, and build real-world projects like time-lapses and motion detectors.

---

## Tutorial Structure

This tutorial is split into focused documents so you can jump to the section most relevant to your level. If you're brand new, work through them in order. If you have some experience, feel free to skip ahead.

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [Hardware Setup](docs/01-hardware-setup.md) | Connecting the camera, ribbon cable, enabling the interface, verifying detection |
| 02 | [Python Camera Basics](docs/02-python-camera-basics.md) | Picamera2 installation, first script, interactive capture, camera controls |
| 03 | [Picamera2 Architecture](docs/03-picamera2-architecture.md) | Full library architecture, layers, class hierarchy, stream patterns |
| 04 | [Practical Projects](docs/04-projects.md) | Time-lapse, button-triggered capture, motion detection, video recording |
| 05 | [Troubleshooting](docs/05-troubleshooting.md) | Common errors, fixes, diagnostic commands |

---

## Quick Start

If you just want to get a photo captured as fast as possible, here's the minimum you need.

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
|----------|--------|----|
| Raspberry Pi 4 Model B | Camera Module 3 | Raspberry Pi OS Bookworm (64-bit) |
| Raspberry Pi Zero 2 W | Camera Module v2 | Raspberry Pi OS Bullseye (32-bit) |

---

## Contributing

Contributions are welcome! If you spot an error, want to add a project, or have a better explanation for something, please open an issue or submit a pull request.

---

## License

This tutorial is released under the [MIT License](LICENSE). All code examples are free to use, modify, and share.
