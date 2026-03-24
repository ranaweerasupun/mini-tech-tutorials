# 07 — Troubleshooting

GStreamer errors can be intimidating because they are often terse and assume
familiarity with the framework. This guide decodes the most common errors you
will encounter working through this tutorial, explains what is actually going
wrong, and gives you a structured way to diagnose problems you have not seen
before.

---

## The Diagnostic Mindset

Before looking at specific errors, it helps to understand how to approach
GStreamer debugging generally. The right mental model is to think of the pipeline
as a chain and ask: at which link did the chain break? GStreamer errors almost
always point to a specific element, and the element name in the error message
tells you where in the chain to focus your attention.

The two most useful diagnostic tools are already on your system. The first is
`GST_DEBUG`, an environment variable that enables verbose logging from inside
GStreamer's internals. Setting it to `3` gives you warnings and errors:

```bash
GST_DEBUG=3 python3 your_script.py
```

Setting it to `5` gives you everything — including format negotiation details,
which is invaluable for caps-related failures:

```bash
GST_DEBUG=v4l2:5,caps:5 python3 your_script.py 2>&1 | less
```

The `element_name:level` syntax restricts verbose logging to specific categories
rather than flooding you with output from every element. The second tool is
`gst-inspect-1.0`, which tells you exactly what formats an element can accept
and produce — this is your primary reference when a caps negotiation fails.

---

## Error: "could not link" or "failed to negotiate"

This is the most common error for beginners, and it is always a caps
incompatibility. It means two adjacent elements in your pipeline could not
find a common format to agree on.

The first step is to identify *which* two elements could not be linked. The
error message usually names one of them. Once you know the pair, check what
formats each element supports:

```bash
# What can v4l2h264enc accept on its input?
gst-inspect-1.0 v4l2h264enc | grep -A 10 "Sink Caps"

# What can v4l2convert produce on its output?
gst-inspect-1.0 v4l2convert | grep -A 10 "Source Caps"
```

The fix is almost always to insert an explicit caps filter that specifies a
format that both elements support. For the hardware encoder pipeline in this
tutorial, `video/x-raw,format=I420` between `v4l2convert` and `v4l2h264enc`
resolves the majority of negotiation failures. If you omitted this filter and
are seeing a link failure, add it and try again.

If the error persists after adding the I420 filter, try checking your camera's
supported formats. The caps filter you placed after `v4l2src` may be requesting
a resolution or framerate your camera does not actually support:

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Find a resolution and framerate that appear in the output and use those values
in your caps filter.

---

## Error: "v4l2h264enc: Failed to allocate required memory"

This means the hardware encoder cannot allocate DMA buffers. On the Raspberry
Pi, DMA buffers come from a shared memory pool that is split between the CPU
and the GPU. If the GPU memory allocation is too small, the hardware codec
cannot get the buffers it needs.

Check `/boot/firmware/config.txt` and look for a `gpu_mem` line. If you do not
see one, or if it is set below 128, add or change it:

```bash
sudo nano /boot/firmware/config.txt
```

Add this line in the `[all]` section:

```
gpu_mem=128
```

Then reboot. On the Pi 5, the memory split is managed differently from
earlier Pi models, but `gpu_mem=128` remains the correct minimum for hardware
video encoding to function reliably.

---

## Error: "No such element or plugin 'v4l2h264enc'"

GStreamer cannot find the hardware encoder element. This means either the
`gstreamer1.0-v4l2` package is not installed, or it is installed but the
hardware codec device is not available.

First, confirm the package is installed:

```bash
sudo apt install -y gstreamer1.0-v4l2
```

Then confirm the hardware codec device exists:

```bash
v4l2-ctl --list-devices | grep bcm2835
```

If `bcm2835-codec` does not appear, the kernel module has not loaded. Try
rebooting. If it still does not appear after a reboot and you are on a
Raspberry Pi 5 with Bookworm, confirm the OS image is recent — this hardware
codec support was added in relatively recent kernel versions.

---

## Error: "Device /dev/video0 failed to start"

`v4l2src` could not open or start the camera. There are several possible causes,
and it is worth checking them in order.

First, confirm the camera is physically connected and the device exists:

```bash
ls /dev/video*
```

If `/dev/video0` does not appear, the camera is not recognised by the kernel.
Unplug it, wait five seconds, and plug it back in. Then run `dmesg | tail -20`
to see if the kernel logged any errors during the reconnection.

Second, confirm your user has permission to access the camera device:

```bash
ls -la /dev/video0
```

The output will show something like `crw-rw----  1 root video  81, 0`. If your
user is not in the `video` group, you will get a permission denied error. Fix
this with:

```bash
sudo usermod -aG video $USER
```

Then log out and log back in for the group membership to take effect.

Third, confirm no other process is using the camera. On Linux, V4L2 camera
devices can only be opened by one application at a time. If a previous script
crashed without closing the device properly, or if another application has the
camera open, you will get this error:

```bash
# Find what process is using the camera device
sudo lsof /dev/video0
```

If you see a process listed, kill it and try again.

---

## Pipeline Runs But Output File is Unplayable

If the script ran successfully but the output `.mp4` file will not open in a
media player, the most likely cause is that the file was not closed cleanly.
The `mp4mux` element writes its index structure (the moov atom, which tells
players where each frame is located in the file) at the very end, when it
receives an end-of-stream signal during shutdown.

If you stopped the script with `kill -9` (which sends SIGKILL, which cannot
be caught or handled), the pipeline never got a chance to send the EOS signal,
and the index was never written. The file exists but is incomplete.

The example scripts in this tutorial handle this correctly by catching SIGINT
(Ctrl+C) and sending an EOS signal before transitioning the pipeline to NULL.
Always use Ctrl+C to stop a recording script, not `kill -9`. If you do end
up with a corrupt file, VLC can sometimes recover it — open the file in VLC
and it will usually offer to fix it automatically.

---

## Output Video is Blocky or Corrupted-Looking

If the video plays but looks heavily artefacted — especially at the start, or
when seeking — the SPS and PPS headers are probably missing or infrequent.
These headers contain the information a decoder needs to initialise itself for
the specific video stream.

For the software encoder, ensure `h264parse` has `config-interval=1` set. For
the hardware encoder, ensure `extra-controls` includes `repeat_sequence_header=1`.
Both of these properties cause headers to be embedded regularly throughout the
stream rather than only once at the very beginning, which is what allows seeking
and mid-stream decoding to work correctly.

---

## CPU Usage is Still High After Switching to Hardware Encoding

If you switched to `v4l2h264enc` but CPU usage is still as high as with
software encoding, the zero-copy DMA path is probably not being used. Check
whether `v4l2convert` is in the pipeline — if you still have `videoconvert`,
GStreamer is doing the pixel format conversion in CPU memory and the frames
never make it into DMA buffers before reaching the hardware encoder.

To confirm whether DMA buffer passing is working, enable verbose V4L2 logging:

```bash
GST_DEBUG=v4l2:5 python3 03_hardware_encode.py 2>&1 | grep -i "dma\|dmabuf"
```

If you see messages about DMA buffer allocation and passing, the zero-copy
path is active. If you see messages about fallback to regular memory copies,
check that `v4l2convert` is in the pipeline and that the I420 caps filter
is present between `v4l2convert` and `v4l2h264enc`.

---

## Quick Reference: Diagnostic Commands

These commands cover the majority of diagnostic needs when something is not
working and the error message alone is not enough to identify the cause.

```bash
# List all V4L2 devices (cameras and hardware codecs)
v4l2-ctl --list-devices

# Show all formats and resolutions a specific camera supports
v4l2-ctl -d /dev/video0 --list-formats-ext

# Describe a GStreamer element and its capabilities
gst-inspect-1.0 v4l2h264enc
gst-inspect-1.0 v4l2convert

# Run a pipeline with verbose error logging
GST_DEBUG=3 gst-launch-1.0 your-pipeline-here

# Run with verbose caps negotiation logging
GST_DEBUG=caps:5 gst-launch-1.0 your-pipeline-here 2>&1 | grep -i "caps\|negotiate"

# Check GPU temperature and throttling (affects encoding performance)
vcgencmd measure_temp
vcgencmd get_throttled

# Find what is using a camera device
sudo lsof /dev/video0

# Check system journal for kernel-level camera or codec errors
journalctl -k | grep -iE "v4l2|video|codec|bcm2835"
```
