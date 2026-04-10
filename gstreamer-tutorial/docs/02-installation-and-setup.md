<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 02 — Installation and Setup

Let's get GStreamer installed, confirm the hardware encoder is present, and run a quick test to make sure the camera is working — all before writing a single line of Python.

---

## Installing GStreamer

GStreamer is split across several packages. The core library is small, but the actual elements you use every day — codecs, camera readers, file writers — live in separate plugin packages. This split exists for licensing reasons: some codecs like H.264 have patent considerations, so they live in the "bad" or "ugly" packages rather than the fully open-source "good" package. Don't let the names put you off — for a Raspberry Pi project you want all of them.

```bash
sudo apt update
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-v4l2 \
    python3-gst-1.0 \
    v4l2-utils
```

What each package contributes: `gstreamer1.0-tools` installs the `gst-launch-1.0` and `gst-inspect-1.0` command-line tools you'll use constantly for testing. `gstreamer1.0-plugins-base` contains foundational elements like `videoconvert` and `playbin`. `gstreamer1.0-plugins-good` contains well-maintained elements including `v4l2src` (for reading cameras) and `mp4mux` (for writing MP4 files). `gstreamer1.0-plugins-bad` contains functional but not yet fully polished elements — `v4l2h264enc`, the hardware encoder we care about, lives here. `gstreamer1.0-plugins-ugly` contains elements that work well but have licensing complexity — `x264enc`, the software H.264 encoder, lives here. `gstreamer1.0-v4l2` contains the complete V4L2 integration including the hardware codec elements. `python3-gst-1.0` is the Python binding package. `v4l2-utils` installs `v4l2-ctl`, a command-line tool for querying and controlling camera and codec hardware.

---

## Verify the Installation

Once installation completes, confirm the core tools are available:

```bash
gst-launch-1.0 --version
```

You should see something like `gst-launch-1.0 version 1.22.x`. If the command is not found, `gstreamer1.0-tools` didn't install correctly — re-run the `apt install` command above.

Then confirm the Python bindings work:

```bash
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; print('GStreamer', Gst.version_string())"
```

If this prints a version string, Python can talk to GStreamer. If it raises an `ImportError`, ensure `python3-gst-1.0` is installed.

---

## Verify the Hardware Encoder

This step only applies to the Raspberry Pi 5. The hardware H.264 encoder is implemented as a V4L2 device, meaning it appears in the system as a video device alongside your webcam.

List all V4L2 devices on the system:

```bash
v4l2-ctl --list-devices
```

Look for an entry containing `bcm2835-codec` — that's the Broadcom VideoCore hardware codec block. It'll look something like this:

```
bcm2835-codec-encode (platform:bcm2835-codec):
    /dev/video11
    /dev/video12
```

The exact device numbers can vary between kernel versions, but that's fine — GStreamer's `v4l2h264enc` element finds the right device automatically. What matters is that the `bcm2835-codec` entry appears at all. If it doesn't, the video codec kernel module hasn't loaded. Try rebooting, and if it still doesn't appear, confirm you're running a recent Raspberry Pi OS Bookworm image.

Now confirm GStreamer can see the hardware encoder element:

```bash
gst-inspect-1.0 v4l2h264enc
```

This prints everything GStreamer knows about an element — its properties, its pad capabilities, and which plugin package it belongs to. Several pages of output means the element is available. `No such element or plugin 'v4l2h264enc'` means the `gstreamer1.0-v4l2` package needs to be (re)installed.

---

## Finding the Webcam

Plug in your USB webcam if you haven't already. Confirm the system sees it:

```bash
v4l2-ctl --list-devices
```

You should see your webcam listed alongside the hardware codec, under its manufacturer name:

```
USB Camera (usb-0000:01:00.0-1.1):
    /dev/video0
    /dev/video1
```

The device you want to use in your pipeline is typically `/dev/video0`. If you have multiple cameras or if the codec devices are assigned lower numbers on your system, the number might be different — use whatever device number appears under your camera's name.

To confirm the camera can actually produce video at the format we need:

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Look for `MJPEG` in the output, and note what resolutions it supports. You need `1280x720` at `30fps` in MJPEG for the examples in this tutorial. If your camera doesn't support that exact mode, find the closest match and adjust the pipeline caps filters accordingly. The entries look like this:

```
[1]: 'MJPG' (Motion-JPEG, compressed)
     Size: Discrete 1280x720
         Interval: Discrete 0.033s (30.000 fps)
```

---

## A Quick Sanity Check

Before writing any Python, run this one-liner to confirm GStreamer can open the camera and produce video frames:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegdec ! videoconvert ! autovideosink
```

This should open a window showing the live camera feed. If you see yourself (or whatever the camera is pointed at), GStreamer, your camera, and your display are all working. Press Ctrl+C to stop.

If you're working headlessly over SSH without a monitor, replace `autovideosink` with `fakesink`:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegdec ! videoconvert ! fakesink
```

`fakesink` discards the video output but still runs the pipeline and verifies the camera is readable. If this runs without errors (you'll see lines of timing output scrolling by), everything is working. Press Ctrl+C to stop.

If you see an error at this stage, stop here and check the [Troubleshooting guide](07-troubleshooting.md) before continuing — there's nothing to be gained from pushing into the Python scripts if the camera or GStreamer itself isn't working.

**Next: [03 — Your First Pipeline](03-your-first-pipeline.md)**
