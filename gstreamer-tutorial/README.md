# GStreamer on Raspberry Pi 5 — A Beginner's Guide

[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/Content-CC--BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

A beginner-friendly, open-source tutorial for Python developers who want to build video pipelines with GStreamer on the Raspberry Pi 5. We'll go from "never heard of GStreamer" to capturing webcam video and encoding it to an H.264 file using the Pi 5's hardware video encoder — dropping CPU usage from ~80% to ~15% in the process.

No prior GStreamer experience needed. If you can write a Python script, you have everything you need to start.

---

## What We'll Build

By the end of this tutorial you'll have a Python script that:

- Captures live video from a USB webcam at 720p30
- Encodes it to H.264 using the Pi 5's built-in hardware encoder (not the CPU)
- Saves the result as a playable MP4 file

Along the way we'll cover *why* every line exists — not just what to copy and paste.

---

## Tutorial Structure

Work through these documents in order. Each one builds directly on the last.

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [What is GStreamer?](docs/01-what-is-gstreamer.md) | Pipelines, elements, pads, and caps — the mental model you need before touching any code |
| 02 | [Installation & Setup](docs/02-installation-and-setup.md) | Installing GStreamer, verifying the hardware encoder exists, pointing a camera at a test pipeline |
| 03 | [Your First Pipeline](docs/03-your-first-pipeline.md) | Using `gst-launch-1.0` to build and test pipelines from the terminal — the fastest feedback loop there is |
| 04 | [GStreamer in Python](docs/04-gstreamer-in-python.md) | The PyGObject bindings, `parse_launch`, pipeline states, and the bus |
| 05 | [Software Encoding](docs/05-software-encoding.md) | Capturing webcam video to a file with x264 — the baseline before hardware encoding |
| 06 | [Hardware Encoding](docs/06-hardware-encoding.md) | Switching to v4l2h264enc — what changes, what doesn't, and why the specific changes are necessary |
| 07 | [Troubleshooting](docs/07-troubleshooting.md) | Common error messages decoded, diagnostic commands, and a structured way to find what broke |

---

## Quick Start

If you want a working script immediately and will read the explanations later:

```bash
# Install GStreamer
sudo apt update
sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly gstreamer1.0-v4l2 \
    python3-gst-1.0 v4l2-utils

# Run the hardware-encoding example
python3 examples/webcam-to-file/03_hardware_encode.py
```

A file called `output_hardware.mp4` will appear in the current directory after you stop the script with Ctrl+C.

---

## Examples

All example scripts live in [`examples/webcam-to-file/`](examples/webcam-to-file/), numbered to reflect the order you should read and run them:

- [`01_test_pipeline.py`](examples/webcam-to-file/01_test_pipeline.py) — The absolute minimum: open a camera and verify it produces frames
- [`02_software_encode.py`](examples/webcam-to-file/02_software_encode.py) — Capture to file using x264 (CPU encoding)
- [`03_hardware_encode.py`](examples/webcam-to-file/03_hardware_encode.py) — Capture to file using v4l2h264enc (hardware encoding)
- [`04_pipeline_builder.py`](examples/webcam-to-file/04_pipeline_builder.py) — The same hardware pipeline built element-by-element with full comments

---

## Requirements

- Raspberry Pi 5 running Raspberry Pi OS Bookworm (64-bit recommended)
- A USB webcam (any UVC-compatible webcam — most modern webcams work)
- Python 3.9 or newer
- Basic Python familiarity — no GStreamer experience needed

The hardware encoder (`v4l2h264enc`) is specific to the Raspberry Pi 5. The software encoding examples will run on any Pi model or Linux system with GStreamer installed.

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
