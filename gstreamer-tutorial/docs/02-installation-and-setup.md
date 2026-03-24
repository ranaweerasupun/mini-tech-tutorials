# 02 — Installation and Setup

This document gets GStreamer installed on your Raspberry Pi 5, confirms that
the hardware encoder is present and accessible, and points your webcam at a
working test pipeline so you know the physical hardware is ready before you
write a single line of Python.

---

## Installing GStreamer

GStreamer is split into several packages. The core library is small, but the
actual elements you use every day — the codecs, the camera readers, the file
writers — live in separate plugin packages. This separation exists for licensing
reasons: some codecs (like H.264) have patent considerations, so they live in
the "bad" or "ugly" packages rather than the fully open-source "good" package.
Do not worry about the names — for a Raspberry Pi project you want all of them.

Run the following to install everything you need:

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

Here is what each package contributes. `gstreamer1.0-tools` installs the
`gst-launch-1.0` and `gst-inspect-1.0` command-line tools you will use
constantly for testing. `gstreamer1.0-plugins-base` contains the foundational
elements like `videoconvert`, `audioresample`, and `playbin`. `gstreamer1.0-plugins-good`
contains well-maintained elements including `v4l2src` (for reading cameras) and
`mp4mux` (for writing MP4 files). `gstreamer1.0-plugins-bad` contains elements
that are functional but not yet fully polished — `v4l2h264enc`, the hardware
encoder we care about, lives here. `gstreamer1.0-plugins-ugly` contains elements
that work well but have licensing complexity — `x264enc`, the software H.264
encoder, lives here. `gstreamer1.0-v4l2` contains the complete V4L2 integration
including the hardware codec elements. `python3-gst-1.0` is the Python binding
package — this is what lets you control GStreamer from Python code. `v4l2-utils`
installs `v4l2-ctl`, a command-line tool for querying and controlling camera and
codec hardware.

---

## Verifying the Installation

Once installation completes, confirm the core tools are available:

```bash
gst-launch-1.0 --version
```

You should see something like `gst-launch-1.0 version 1.22.x`. If the command
is not found, the `gstreamer1.0-tools` package did not install correctly —
re-run the `apt install` command above.

Next, confirm the Python bindings work:

```bash
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; print('GStreamer', Gst.version_string())"
```

If this prints a version string, Python can talk to GStreamer. If it raises an
`ImportError`, ensure `python3-gst-1.0` is installed.

---

## Verifying the Hardware Encoder

This step only applies to the Raspberry Pi 5. The hardware H.264 encoder is
implemented as a V4L2 device, which means it appears in the system as a video
device alongside your webcam.

List all V4L2 devices on the system:

```bash
v4l2-ctl --list-devices
```

In the output, look for an entry containing `bcm2835-codec` — that is the
Broadcom VideoCore hardware codec block. It will look something like this:

```
bcm2835-codec-encode (platform:bcm2835-codec):
    /dev/video11
    /dev/video12
```

The exact device numbers (`/dev/video11` etc.) can vary between kernel versions,
but that is fine — GStreamer's `v4l2h264enc` element finds the right device
automatically. What matters is that the `bcm2835-codec` entry appears at all.
If it does not appear, the video codec kernel module has not loaded. Try
rebooting, and if it still does not appear, confirm you are running a recent
Raspberry Pi OS Bookworm image.

Now confirm GStreamer can see the hardware encoder element:

```bash
gst-inspect-1.0 v4l2h264enc
```

This command prints everything GStreamer knows about an element — its
properties, its pad capabilities, and which plugin package it belongs to.
If you see several pages of output, the element is available. If you see
`No such element or plugin 'v4l2h264enc'`, the `gstreamer1.0-v4l2` package
needs to be (re)installed.

---

## Finding Your Webcam

Plug in your USB webcam if you have not already. Confirm the system sees it:

```bash
v4l2-ctl --list-devices
```

You should see your webcam listed alongside the hardware codec. It will appear
under its manufacturer name, something like:

```
USB Camera (usb-0000:01:00.0-1.1):
    /dev/video0
    /dev/video1
```

The device you want to use in your pipeline is typically `/dev/video0`. If you
have multiple cameras plugged in, or if the codec devices are assigned lower
numbers on your system, the number might be different — use whatever device
number appears under your camera's name.

To confirm the camera can actually produce video, ask it what formats it supports:

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Look for `MJPEG` in the output, and note what resolutions it supports at what
frame rates. You need `1280x720` at `30fps` in MJPEG for the examples in this
tutorial. If your camera does not support that exact mode, find the closest
match it does support and adjust the pipeline caps filters accordingly. The
format entries look like this:

```
[1]: 'MJPG' (Motion-JPEG, compressed)
     Size: Discrete 1280x720
         Interval: Discrete 0.033s (30.000 fps)
```

---

## A Quick Sanity Test

Before writing any Python, run this one-liner from the terminal to confirm that
GStreamer can open the camera and produce video frames:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegdec ! videoconvert ! autovideosink
```

This should open a window showing the live camera feed. If you see yourself
(or whatever the camera is pointed at), GStreamer, your camera, and your display
are all working correctly. Press Ctrl+C to stop it.

If a display window is not available because you are working headlessly over SSH,
replace `autovideosink` with `fakesink` — that discards the video output but
still runs the pipeline and verifies the camera is readable:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegdec ! videoconvert ! fakesink
```

If this runs without errors (you will see lines of timing output scrolling by),
everything is working. Press Ctrl+C to stop.

If you see an error at this stage, stop here and consult the
[Troubleshooting guide](07-troubleshooting.md) before continuing.

**Next: [03 — Your First Pipeline](03-your-first-pipeline.md)**
