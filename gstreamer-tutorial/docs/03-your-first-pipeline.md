<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 03 — Your First Pipeline

Before writing any Python, spend some time with `gst-launch-1.0` — GStreamer's command-line pipeline runner. Think of it as a REPL for pipelines. You type a pipeline string, press Enter, and it runs immediately. No script to create, no boilerplate to write. This tight feedback loop is the fastest way to learn pipeline construction and to debug problems, because you can isolate each element and test it independently before combining everything together.

Every working Python GStreamer script in this tutorial started life as a `gst-launch-1.0` command. Learn this tool first and the Python code will feel like a natural translation rather than a leap into the unknown.

---

## The Basic Syntax

```
gst-launch-1.0  element1 [property=value ...]  !  element2 [property=value ...]  !  ...
```

Each element name is followed by any number of `property=value` pairs that configure it. Elements are linked together with `!`. The whole thing is one long string passed to the command.

---

## Step 1 — The Minimal Pipeline: Source to Sink

The simplest meaningful pipeline has exactly two elements: a source and a sink. Try this one, which generates a test video signal entirely in software (no camera needed):

```bash
gst-launch-1.0 videotestsrc ! autovideosink
```

`videotestsrc` generates synthetic video frames — a colour bars pattern by default. `autovideosink` opens a window and displays them. If you see a moving colour pattern, GStreamer, its display integration, and your environment are all working. Press Ctrl+C to stop.

Now try changing a property. The `pattern` property of `videotestsrc` accepts different test patterns:

```bash
gst-launch-1.0 videotestsrc pattern=snow ! autovideosink
```

This produces static noise instead of colour bars. Any `key=value` pair after an element name sets a property on that element. You can discover what properties an element accepts with `gst-inspect-1.0`:

```bash
gst-inspect-1.0 videotestsrc
```

The output lists every property, its type, its default value, and what it does. This is the GStreamer equivalent of reading a function's docstring — get comfortable using it.

---

## Step 2 — Adding a Caps Filter

Try constraining the format of the video with a caps filter:

```bash
gst-launch-1.0 videotestsrc ! video/x-raw,width=640,height=480 ! autovideosink
```

The `video/x-raw,width=640,height=480` part between the `!` characters is not an element — it's a caps filter. It tells GStreamer that the data flowing through that point must be raw video at 640×480. If `videotestsrc` can produce that format, it will. Ask for something it can't produce and the pipeline fails with a negotiation error.

Caps filters are your way of being explicit about what you want. Without them, GStreamer negotiates automatically, which often works fine — but sometimes picks a format you didn't expect. Being explicit prevents surprises.

---

## Step 3 — Opening a Real Camera

Replace the test source with a real camera source:

```bash
gst-launch-1.0 v4l2src device=/dev/video0 ! jpegdec ! videoconvert ! autovideosink
```

Three elements are working together here. `v4l2src` opens the device at `/dev/video0` and streams frames from it. The camera produces MJPEG-compressed frames rather than raw video — this is normal for USB webcams because MJPEG is much smaller than raw video, so more data fits through the USB bandwidth at higher resolutions. Because the frames are MJPEG-compressed, they need to be decompressed before anything else in the pipeline can work with them, which is what `jpegdec` does. After decompression you have raw video frames, but they may be in a pixel format that `autovideosink` can't display directly — `videoconvert` handles that translation.

If your camera is at a different device path, substitute `/dev/video0` with the correct path from `v4l2-ctl --list-devices`.

---

## Step 4 — Constraining the Camera Format

Without a caps filter, `v4l2src` will negotiate whatever format your camera defaults to, which might not be MJPEG at the resolution you want. Add an explicit caps filter right after `v4l2src`:

```bash
gst-launch-1.0 \
    v4l2src device=/dev/video0 \
    ! image/jpeg,width=1280,height=720,framerate=30/1 \
    ! jpegdec \
    ! videoconvert \
    ! autovideosink
```

Two things worth noticing here. The format name for MJPEG as delivered by a camera is `image/jpeg` — not `video/x-jpeg` or `video/mjpeg`. This trips people up constantly. And the framerate is written as `30/1`, not `30` — GStreamer represents framerates as fractions for precision. `30/1` means exactly 30 frames per second. Some cameras use `30000/1001` (≈29.97 fps, the NTSC standard) rather than exactly 30, and GStreamer will reject the pipeline if you request `30/1` from a camera that only supports `30000/1001`. If you get a negotiation failure, check your camera's supported framerates with `v4l2-ctl -d /dev/video0 --list-formats-ext`.

---

## Step 5 — Saving to a File

Replace `autovideosink` with a chain of elements that encode and save the video:

```bash
gst-launch-1.0 \
    v4l2src device=/dev/video0 \
    ! image/jpeg,width=1280,height=720,framerate=30/1 \
    ! jpegdec \
    ! videoconvert \
    ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000 \
    ! h264parse config-interval=1 \
    ! mp4mux \
    ! filesink location=test_output.mp4
```

Two new elements at the end. `x264enc` is the software H.264 encoder. `tune=zerolatency` optimises it for real-time capture, minimising the delay between a frame arriving and being encoded. `speed-preset=ultrafast` uses the fastest, least CPU-intensive compression setting at the cost of a slightly larger file. `bitrate=2000` sets the target bitrate to 2000 kbps.

`h264parse` reads the H.264 stream and ensures its structure is correct for downstream consumers. The `config-interval=1` property tells it to insert the stream's configuration headers (SPS and PPS) at every keyframe rather than only at the very beginning — this makes the file more robust and lets video players seek into it correctly.

`mp4mux` wraps the H.264 stream in an MP4 container, and `filesink` writes it to disk.

Run this for ten seconds, then press Ctrl+C. Open `test_output.mp4` in VLC or any media player — you should have a working video file.

---

## Reading gst-launch-1.0 Output

While a pipeline is running, `gst-launch-1.0` prints status information:

```
Setting pipeline to PAUSED ...
Pipeline is PREROLLING ...
Pipeline is PREROLLED ...
Setting pipeline to PLAYING ...
New clock: GstSystemClock
```

"PREROLLING" means elements are getting ready — negotiating formats, opening files, initialising hardware. "PREROLLED" means all elements are ready and the pipeline is about to start flowing data. "PLAYING" means data is actively flowing.

If the pipeline fails during PREROLLING, it's almost always a caps negotiation error or a missing element. The error message in this phase is your most useful diagnostic tool. Failure during PLAYING usually means a runtime problem — hardware issues, disk full, camera disconnected.

---

## gst-inspect-1.0: Your Reference Tool

Before moving to Python, get comfortable with `gst-inspect-1.0`. It's the most useful reference you have for understanding what an element can do:

```bash
# Describe a specific element
gst-inspect-1.0 x264enc

# Describe the hardware encoder
gst-inspect-1.0 v4l2h264enc

# List all available elements (long output — pipe to grep to filter)
gst-inspect-1.0 | grep h264
```

When you're not sure what properties an element accepts, or what caps it can produce or consume, `gst-inspect-1.0` is where you look first. It's faster and more reliable than searching the internet, and more accurate than asking an AI.

**Next: [04 — GStreamer in Python](04-gstreamer-in-python.md)**
