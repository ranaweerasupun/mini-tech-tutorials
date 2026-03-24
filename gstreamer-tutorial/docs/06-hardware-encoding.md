# 06 — Hardware Encoding

You now have a working software pipeline and an intuition for what each element
does. This document makes the switch to hardware encoding. The pipeline barely
changes — three elements are modified and one caps filter is added — but
understanding *why* those specific changes are necessary will save you from
the confusion that most people hit when they try to make this switch blindly.

---

## Why the Hardware Encoder Needs Special Treatment

The conceptual model here is important, so spend a moment on it before looking
at any code.

The software encoder (`x264enc`) is just a C library. It accepts raw video
frames in a wide variety of pixel formats, does all its work in RAM using the
CPU, and produces H.264 output. Because it lives entirely in software, GStreamer
can hand it any format it can handle and the library sorts out the rest.

The hardware encoder (`v4l2h264enc`) is fundamentally different. It is a
dedicated silicon block — a piece of hardware on the VideoCore VII chip inside
the Raspberry Pi 5 — that has its own memory space and speaks its own interface.
GStreamer communicates with it through V4L2 (Video for Linux 2), the kernel
subsystem that provides a standard interface to video hardware. Because it is
hardware, it only accepts very specific input formats and memory layouts. You
cannot just hand it a frame and hope it figures things out.

The key constraint is this: the hardware encoder expects frames to arrive in
**DMA-allocated memory buffers** — memory regions that are directly accessible
by the GPU hardware, not ordinary CPU-allocated RAM. A frame sitting in
regular Python memory cannot be fed to the hardware encoder without first being
copied into a DMA buffer. That copy would cost CPU time and largely defeat the
purpose of using hardware encoding in the first place.

GStreamer solves this with a special V4L2-aware converter called `v4l2convert`.
Unlike the ordinary `videoconvert`, which does its work in CPU memory,
`v4l2convert` uses zero-copy DMA buffer passing. Once a frame enters `v4l2convert`,
it lives in GPU-accessible DMA memory for the rest of the pipeline — through
the converter and straight into the hardware encoder — with no CPU copying. This
is the core reason CPU usage drops so dramatically.

---

## What Changes in the Pipeline

Here is the before and after, side by side:

**Software pipeline:**
```
v4l2src → jpegdec → videoconvert → x264enc → h264parse → mp4mux → filesink
```

**Hardware pipeline:**
```
v4l2src → jpegdec → v4l2convert → [I420 caps] → v4l2h264enc → [h264 level caps] → h264parse → mp4mux → filesink
```

Three things changed. `videoconvert` became `v4l2convert`. `x264enc` became
`v4l2h264enc`. Two explicit caps filters were added that were not needed before.

Let us go through each change in turn.

---

### Change 1: `videoconvert` → `v4l2convert`

This is the change that enables zero-copy DMA buffer passing as described above.
The `v4l2convert` element is part of the `gstreamer1.0-v4l2` plugin package and
is specifically designed to work with V4L2 hardware. It performs the same pixel
format conversion that `videoconvert` does, but in a way that leaves the frame
in GPU-accessible memory for the hardware encoder to read directly.

If you leave `videoconvert` in the pipeline when using `v4l2h264enc`, the
pipeline may still work — GStreamer will insert implicit format conversions to
bridge the incompatibility — but you will not get zero-copy DMA, and your CPU
usage will be much higher than it should be. The whole point of hardware
encoding is undermined. Use `v4l2convert` when targeting `v4l2h264enc`.

---

### Change 2: Add `video/x-raw,format=I420` caps filter

After `v4l2convert` and before `v4l2h264enc`, you need to insert an explicit
caps filter specifying the pixel format:

```
! v4l2convert ! video/x-raw,format=I420 ! v4l2h264enc
```

**I420** is the standard YUV 4:2:0 planar format. "YUV" means the colour
information is stored as one brightness (luma, Y) channel and two colour
(chroma, U and V) channels. "4:2:0" means the chroma channels are sampled at
half the horizontal and vertical resolution of the luma channel — this is
possible because human eyes are far more sensitive to brightness differences
than to colour differences, so you can throw away colour detail without the
result looking wrong. "Planar" means the Y, U, and V channels are stored in
separate memory regions rather than interleaved.

Without this caps filter, GStreamer's automatic format negotiation might select
a different pixel format — one that the hardware encoder cannot accept. Adding
the explicit I420 filter removes the ambiguity and prevents a class of
negotiation failures that are otherwise very hard to debug. The hardware encoder
on the Pi 5 reliably accepts I420.

---

### Change 3: `x264enc` → `v4l2h264enc` with extra-controls

```
! v4l2h264enc extra-controls="controls,repeat_sequence_header=1"
```

`v4l2h264enc` is the GStreamer element that communicates with the VideoCore
hardware encoder. Unlike `x264enc`, which has many conventional GStreamer
properties, the hardware encoder exposes its tuning parameters through V4L2
controls — a lower-level hardware interface. The `extra-controls` property
passes these V4L2 controls directly to the hardware.

`repeat_sequence_header=1` is the hardware equivalent of `h264parse`'s
`config-interval=1`. It tells the encoder to embed the SPS and PPS headers
(described in the previous document) periodically in the stream rather than
only at the very beginning. For the file recording use case, this makes the
output video more robust and seek-friendly. For streaming use cases, it means
a client that connects mid-stream can start decoding immediately when the next
keyframe arrives rather than waiting for a full stream restart.

---

### Change 4: Add `video/x-h264,level=(string)4` caps filter

```
! v4l2h264enc extra-controls="controls,repeat_sequence_header=1"
! video/x-h264,level=(string)4
! h264parse
```

This caps filter tells downstream elements what H.264 profile level the encoder
is producing. H.264 levels define the maximum resolution, bitrate, and
complexity that a compliant decoder must support. Level 4 supports up to
1080p30, which is more than sufficient for our 720p30 pipeline.

The reason this caps filter is necessary is subtle. Without it, the hardware
encoder's output caps leave the level as "unspecified." Some downstream
elements — particularly `mp4mux` when writing metadata, and `webrtcbin` if you
ever use this pipeline for WebRTC — are strict about requiring a declared level.
Adding this filter proactively prevents a category of negotiation errors you
would otherwise encounter when trying to connect the pipeline to other elements
or tools.

Note that `level=(string)4` uses the string type annotation. This is because
GStreamer's caps system represents H.264 levels as strings to handle the half-
levels (like `4.1`, `4.2`) that the H.264 specification defines. Without
`(string)`, GStreamer interprets `4` as an integer and the caps do not match
the element's expectations.

---

## Setting the Keyframe Interval and Bitrate

The hardware encoder exposes two more important controls through `extra-controls`.

The **keyframe interval** controls how often the encoder produces a full
reference frame (an I-frame) versus a difference frame (a P-frame or B-frame).
I-frames are large but fully self-contained — a decoder can start from any
I-frame without knowing anything about previous frames. P-frames are small
but depend on a previous I-frame or P-frame. A long keyframe interval means
smaller files but worse seek performance and more vulnerability to frame loss.
For a 30fps recording, a keyframe interval of 30 means one full I-frame per
second, which is a reasonable default:

```
extra-controls="controls,repeat_sequence_header=1,h264_i_frame_period=30"
```

The **bitrate** for the hardware encoder is most reliably set through `v4l2-ctl`
before the pipeline starts. Find your encoder device number first:

```bash
v4l2-ctl --list-devices
# Note the /dev/videoN number for bcm2835-codec-encode
```

Then set the bitrate:

```bash
# Set to 2 Mbps (value is in bits per second)
v4l2-ctl -d /dev/video11 --set-ctrl video_bitrate=2000000
```

The example script [`examples/webcam-to-file/03_hardware_encode.py`](../examples/webcam-to-file/03_hardware_encode.py)
runs this `v4l2-ctl` command automatically using Python's `subprocess` module
before starting the pipeline, so you do not need to run it manually.

---

## Observing the CPU Difference

With the hardware pipeline running, open `htop` in a second terminal. You
should now see the GStreamer process consuming around 15–25% CPU total — a
dramatic drop from the 60–80% you saw with software encoding. The hardware
encoder is doing the compression work, but because it is a dedicated silicon
block rather than a software library, its activity does not appear in `htop`'s
CPU measurements at all. The CPU load you do see is the overhead of managing
the pipeline itself: moving frames between elements, running the V4L2 interface,
and writing the output file.

This headroom is the practical benefit of hardware encoding. On a Pi 5 running
a full application — handling multiple network connections, running a web
interface, managing GPIO, or running lightweight inference — the difference
between 80% and 15% CPU on the encoder is often the difference between a
responsive system and one that is constantly at the edge of its capacity.

**Next: [07 — Troubleshooting](07-troubleshooting.md)**
