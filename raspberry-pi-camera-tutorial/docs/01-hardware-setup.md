# 01 — Hardware Setup

Before you write a single line of Python, you need to physically connect the camera to your Raspberry Pi and verify that the operating system can see it. This document walks you through every step of that process, from choosing the right cable to running your first test capture from the terminal.

---

## Which Camera Module Do You Have?

There are several official Raspberry Pi camera modules, and knowing which one you have matters because they have different capabilities:

| Module | Resolution | Autofocus | Notes |
|--------|-----------|-----------|-------|
| Camera Module v1 | 5MP | No | Oldest, discontinued but still works |
| Camera Module v2 | 8MP | No | Common, reliable, good value |
| Camera Module 3 | 12MP | Yes (standard version) | Latest, best image quality |
| HQ Camera | 12MP | No (manual via lens) | For interchangeable C/CS-mount lenses |
| Camera Module 3 Wide | 12MP | No | Ultra-wide angle, no autofocus |

All of these work with Picamera2 and with this tutorial. The Camera Module 3 will unlock some extra controls like `AfMode` (autofocus mode), but everything else applies equally to all models.

---

## The Ribbon Cable — Handle With Care

The flat, flexible ribbon cable that connects the camera to the Pi is fragile and the most common source of hardware problems. A few important things to know before you touch it:

The cable is **directional**. One side has exposed metal contacts and the other side is plain blue. The contacts must face the correct direction when inserted — toward the connector latch on the Pi, not away from it. If your image is completely black or the camera isn't detected, a backwards cable is often the cause.

The cable must be **fully and evenly seated**. If one edge of the cable sits slightly higher than the other inside the connector, the signal won't be clean and you'll get errors or a blank image. Insert it straight down, then press the latch closed while holding the cable in place.

The cable is **not hot-swappable**. Always power down the Pi completely before inserting or removing the camera cable. Plugging or unplugging it while the Pi is powered can damage the camera, the Pi, or both.

---

## Connecting the Camera — Step by Step

### On a Raspberry Pi 4, 3, or Zero 2 W

1. **Power down** the Pi completely and unplug the USB-C power cable.

2. **Locate the CSI connector**. On the Pi 4 and Pi 3, this is the narrow black connector between the HDMI ports and the 3.5mm audio jack, labelled **CAMERA** on the board. On the Pi Zero 2 W, it is the small connector near the center of the board (you'll need a shorter Zero-specific ribbon cable since the standard cable is too wide).

3. **Open the latch** by gently pulling the dark plastic tab upward on both sides. It lifts about 2mm — you don't need to force it.

4. **Insert the ribbon cable** with the exposed metal contacts facing toward the board (toward the HDMI ports on a Pi 4). Slide it straight down until it sits flush and you can't push it any further.

5. **Press the latch closed** by pushing the plastic tab back down firmly on both sides. You should feel a light click.

6. **Position the camera module** so it points in the direction you want. The lens should face out, with the ribbon cable leaving from the bottom of the module.

7. **Power the Pi back on.**

### On a Raspberry Pi 5

The Pi 5 has **two** CSI/DSI combo connectors, both labelled on the board. Either one works for a single camera. The process is the same as above, but the connectors are slightly smaller (15-pin vs 22-pin), so make sure you're using the correct cable for your camera module. Most Camera Module v3 kits include the right cable for the Pi 5.

---

## Enabling the Camera Interface

On **Raspberry Pi OS Bookworm**, the camera interface is enabled by default when using the `libcamera` stack and you typically do not need to do anything extra. However, if you're on an older image or ran into issues, it's worth checking.

Run `raspi-config` in the terminal:

```bash
sudo raspi-config
```

Navigate to **Interface Options → Camera** and make sure it is enabled. Then reboot:

```bash
sudo reboot
```

---

## Verifying the Camera is Detected

Once the Pi has rebooted with the camera connected, run this command to ask libcamera to list the cameras it can find:

```bash
libcamera-hello --list-cameras
```

If everything is working, you'll see output that looks something like this:

```
Available cameras
-----------------
0 : imx708 [4608x2592 10-bit RGGB] (/base/soc/i2c0mux/i2c@1/imx708@1a)
    Modes: 'SRGGB10_CSP2' : 1536x864 [120.13 fps] ...
                            2304x1296 [56.03 fps] ...
                            4608x2592 [14.35 fps] ...
```

The exact numbers will vary depending on which camera module you have. The important part is that at least one camera appears with a model name like `imx708` (Camera Module 3), `imx477` (HQ Camera), or `ov5647` (Camera Module v1).

If you see `No cameras available` or an error, stop here and see the [Troubleshooting guide](05-troubleshooting.md) before continuing.

---

## Taking a Test Shot Without Python

Before we touch Python, it's worth confirming the camera works end-to-end using the built-in command-line tools. This helps you separate hardware problems from software problems later.

Take a quick still photo and display it for five seconds:

```bash
libcamera-hello -t 5000
```

This should open a preview window showing what the camera sees for five seconds. If you're running headless (no monitor), skip this and go straight to:

```bash
libcamera-still -o test.jpg
```

Then check that `test.jpg` exists and has a non-zero file size:

```bash
ls -lh test.jpg
```

You should see something like `2.1M` in the size column. If the file is 0 bytes, or if the command produced errors, check the [Troubleshooting guide](05-troubleshooting.md).

---

## Camera Module Orientation

One thing that trips people up early on is that the camera module is often mounted in a fixed orientation inside an enclosure or on a stand that doesn't match the natural viewing direction. You can correct the image orientation in software — no need to physically rotate the camera — using the `Transform` parameter when configuring Picamera2:

```python
from picamera2 import Picamera2
from libcamera import Transform

picam2 = Picamera2()

# Flip the image vertically (upside-down mount)
config = picam2.create_still_configuration(transform=Transform(vflip=True))

# Flip horizontally (mirror effect)
config = picam2.create_still_configuration(transform=Transform(hflip=True))

# Both flips combined = 180 degree rotation
config = picam2.create_still_configuration(transform=Transform(vflip=True, hflip=True))
```

---

## What's Next?

With the camera physically connected and verified, you're ready to start controlling it from Python. Head to [02 — Python Camera Basics](02-python-camera-basics.md) to write your first camera script.
