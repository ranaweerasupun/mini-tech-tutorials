<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 01 — Hardware Setup

Let's get the camera physically connected and confirmed working before touching any Python. This matters because a partially-seated ribbon cable and a software bug produce similar-looking symptoms — if you know the hardware is solid, you've eliminated half the possible failure space before you write a line of code.

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

All of these work with Picamera2 and this tutorial. The Camera Module 3 unlocks some extra controls like `AfMode` (autofocus mode), but everything else applies equally to all models.

---

## The Ribbon Cable — Handle With Care

The flat, flexible ribbon cable is fragile and the most common source of hardware problems. A few things to know before you touch it:

The cable is **directional**. One side has exposed metal contacts and the other side is plain blue. The contacts must face the correct direction when inserted — toward the connector latch on the Pi, not away from it. If your image is completely black or the camera isn't detected at all, a backwards cable is often the cause.

The cable must be **fully and evenly seated**. If one edge sits slightly higher than the other inside the connector, the signal won't be clean and you'll get errors or a blank image. Insert it straight down, then press the latch closed while holding the cable in place.

The cable is **not hot-swappable**. Always power down the Pi completely before inserting or removing the camera cable. Plugging or unplugging it while the Pi is powered can damage the camera, the Pi, or both.

---

## Connecting the Camera — Step by Step

### On a Raspberry Pi 4, 3, or Zero 2 W

1. **Power down** the Pi completely and unplug the USB-C power cable.

2. **Locate the CSI connector**. On the Pi 4 and Pi 3, this is the narrow black connector between the HDMI ports and the 3.5mm audio jack, labelled **CAMERA** on the board. On the Pi Zero 2 W, it's the small connector near the center of the board — you'll need a shorter Zero-specific ribbon cable since the standard cable is too wide.

3. **Open the latch** by gently pulling the dark plastic tab upward on both sides. It lifts about 2mm — you don't need to force it.

4. **Insert the ribbon cable** with the exposed metal contacts facing toward the board (toward the HDMI ports on a Pi 4). Slide it straight down until it sits flush.

5. **Press the latch closed** by pushing the plastic tab back down firmly on both sides. You should feel a light click.

6. **Position the camera module** so the lens faces out, with the ribbon cable leaving from the bottom of the module.

7. **Power the Pi back on.**

### On a Raspberry Pi 5

The Pi 5 has **two** CSI/DSI combo connectors, both labelled on the board. Either one works for a single camera. The process is the same as above, but the connectors are slightly smaller (15-pin vs 22-pin), so make sure you're using the correct cable for your camera module. Most Camera Module v3 kits include the right cable for the Pi 5.

---

## Enabling the Camera Interface

On **Raspberry Pi OS Bookworm**, the camera interface is enabled by default when using the `libcamera` stack and you typically don't need to do anything extra. But if you're on an older image or ran into issues, it's worth checking:

```bash
sudo raspi-config
```

Navigate to **Interface Options → Camera** and confirm it's enabled. Then reboot:

```bash
sudo reboot
```

---

## Verifying the Camera is Detected

Once the Pi has rebooted with the camera connected, run:

```bash
rpicam-hello --list-cameras
```

If everything's working, you'll see output like this:

```
Available cameras
-----------------
0 : imx708 [4608x2592 10-bit RGGB] (/base/soc/i2c0mux/i2c@1/imx708@1a)
    Modes: 'SRGGB10_CSP2' : 1536x864 [120.13 fps] ...
                            2304x1296 [56.03 fps] ...
                            4608x2592 [14.35 fps] ...
```

The exact numbers vary depending on which camera module you have. The important part is that at least one camera appears with a model name — `imx708` (Camera Module 3), `imx477` (HQ Camera), or `ov5647` (Camera Module v1).

If you see `No cameras available` or an error, stop here and check the [Troubleshooting guide](05-troubleshooting.md) before continuing.

---

## Taking a Test Shot Without Python

Before touching Python, confirm the camera works end-to-end using the built-in command-line tools. This separates hardware problems from software problems.

Take a quick still photo and display it for five seconds:

```bash
rpicam-hello -t 5000
```

This should open a preview window showing what the camera sees. If you're running headless (no monitor), skip straight to:

```bash
rpicam-still -o test.jpg
```

Then check the file exists and has a non-zero size:

```bash
ls -lh test.jpg
```

You should see something like `2.1M` in the size column. A 0-byte file or errors means something's wrong at the hardware level — check the [Troubleshooting guide](05-troubleshooting.md).

---

## Camera Orientation

A common early frustration: the camera is mounted in an orientation that doesn't match the natural viewing direction. You can correct this in software — no need to physically rotate anything — using the `Transform` parameter:

```python
from picamera2 import Picamera2
from libcamera import Transform

picam2 = Picamera2()

# Flip vertically (upside-down mount)
config = picam2.create_still_configuration(transform=Transform(vflip=True))

# Flip horizontally (mirror effect)
config = picam2.create_still_configuration(transform=Transform(hflip=True))

# Both flips combined = 180 degree rotation
config = picam2.create_still_configuration(transform=Transform(vflip=True, hflip=True))
```

**Next: [02 — Python Camera Basics](02-python-camera-basics.md)**