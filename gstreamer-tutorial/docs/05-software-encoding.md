# 05 — Software Encoding

This document builds the complete software-encoded pipeline as a Python script.
The goal is not to produce the most efficient pipeline — that comes in the next
document with hardware encoding. The goal here is to build a fully working,
understandable foundation, so that when you switch to hardware encoding you can
see exactly what changed and why.

---

## What Software Encoding Means

When we say "software encoding," we mean that the H.264 compression algorithm
runs entirely on the Raspberry Pi's CPU cores — the same cores that run your
Python script, your operating system, and everything else. The encoder is a
C library called libx264, and GStreamer exposes it through the `x264enc` element.

libx264 is excellent software. It produces very high-quality H.264 video with
many tuning options. Its limitation on a Raspberry Pi is simply the cost: at
720p30, x264 in `ultrafast` mode consumes roughly 60–80% of a single CPU core.
If your application needs to do anything else at the same time — processing
sensor data, running a web server, handling network connections — that CPU
pressure is a real constraint.

Before we address that limitation, we need a working baseline to measure
against and to understand clearly. That is what this document produces.

---

## The Complete Software Pipeline

Open the example script at
[`examples/webcam-to-file/02_software_encode.py`](../examples/webcam-to-file/02_software_encode.py)
and read through it while following the explanation here.

The pipeline in that script is:

```
v4l2src → [image/jpeg caps] → jpegdec → videoconvert
        → x264enc → h264parse → mp4mux → filesink
```

Let us trace the journey of a single video frame through every element so you
understand what is happening at each step.

**`v4l2src`** opens the webcam device and continuously produces frames.
Most USB webcams deliver their frames in MJPEG (Motion JPEG) format, not raw
video. This is because USB has limited bandwidth — a raw 1280×720 frame at
24 bits per pixel is 2.76 MB. At 30 frames per second that is 83 MB/s, which
exceeds USB 2.0's practical throughput. MJPEG compresses each frame
independently, typically down to 30–100 KB per frame, which fits comfortably
in USB bandwidth. The caps filter `image/jpeg,width=1280,height=720,framerate=30/1`
is placed immediately after `v4l2src` to ensure the camera delivers exactly
this mode rather than defaulting to something else.

**`jpegdec`** decompresses each MJPEG frame back into raw pixels. After
decompression you have uncompressed video — a large array of pixel values
for each frame. This raw form is what every subsequent element in the pipeline
expects to receive. The decompression step is unavoidable: you cannot feed
compressed MJPEG directly into an H.264 encoder. You must first decompress to
raw pixels, then re-compress with the target codec.

**`videoconvert`** converts the raw frame from whatever pixel format `jpegdec`
produced into whatever pixel format `x264enc` expects. Pixel formats describe
how colour information is arranged in memory. JPEG decoded frames are often
in I420 (a planar YUV format) or YUY2 (a packed YUV format), while x264
expects a specific YUV layout. `videoconvert` handles all of these conversions
in software using the libyuv library. The format negotiation between `jpegdec`,
`videoconvert`, and `x264enc` happens automatically — you do not need to specify
anything here unless you want to force a particular intermediate format.

**`x264enc`** compresses the raw frames into H.264. The properties we set on
it are worth understanding individually.

`tune=zerolatency` puts x264 into a mode that minimises the delay between a
frame arriving and an encoded output being produced. Without this, x264 buffers
several frames before producing output in order to make better compression
decisions across a group of frames. With real-time capture, you generally want
each frame encoded as quickly as possible, so `zerolatency` trades some
compression efficiency for immediacy.

`speed-preset=ultrafast` selects the fastest, least CPU-intensive compression
algorithm. x264 has a range of presets from `ultrafast` to `veryslow`. Slower
presets spend more CPU analysing the video to find better ways to compress it,
resulting in smaller files or better quality at the same file size. On a
Raspberry Pi, `ultrafast` is the right choice for live capture — the
slower presets would consume even more CPU without meaningful quality gain
for this use case.

`bitrate=2000` sets the target output bitrate to 2000 kbps (2 Mbps). This is
a reasonable quality level for 720p30 video. Higher values produce larger files
with better visual quality; lower values produce smaller files with more visible
compression artefacts. For reference, YouTube recommends 2.5 Mbps for 720p30
uploads.

**`h264parse`** reads the H.264 stream and ensures its structure is correct.
The `config-interval=1` property tells it to emit SPS (Sequence Parameter Set)
and PPS (Picture Parameter Set) headers with every keyframe. These headers
contain the information a decoder needs to understand the video — resolution,
profile, level, and other parameters. By default x264 only puts them at the
very start of the stream, which means a video player that starts reading the
file from the middle cannot decode it until it finds the headers. Setting
`config-interval=1` makes the file more robust and lets video players seek
freely within it.

**`mp4mux`** wraps the H.264 stream in an MP4 container. H.264 is a codec —
it defines how individual frames are compressed. MP4 is a container format —
it defines how frames are organised on disk with timestamps, seeking tables,
metadata, and the other structures that make a file usable by media players.
Without a container, the raw H.264 stream is harder for players to handle.

**`filesink`** writes the resulting bytes to disk at the path specified by the
`location` property.

---

## Measuring the CPU Cost

Once the script is running, open a second terminal and run `htop`. Look for the
Python process running your script. You will likely see it consuming 60–80% of
one CPU core. The thread doing the heavy lifting is `x264enc` — the software
compression is CPU-intensive by nature.

Remember this number. In the next document you will run the equivalent hardware
pipeline and observe the same measurement drop to around 15–20%.

---

## A Note on the Output File

When you stop the script with Ctrl+C, the pipeline transitions to NULL state
and closes the file. The resulting `output_software.mp4` should be a valid,
playable MP4 file. Copy it off the Pi and open it in VLC, QuickTime, or any
media player to verify it looks correct before moving on.

One common question at this stage: why does the file sometimes fail to open in
a media player if the script was killed with `kill -9` rather than Ctrl+C?
The reason is that `mp4mux` writes the MP4 index (the structure that tells
players where each frame is in the file) at the very end of the file, when it
receives the EOS (end-of-stream) signal during clean shutdown. A forced kill
skips this step, leaving the file without an index. The Ctrl+C handler in the
example script specifically sends EOS before shutting down to avoid this.

**Next: [06 — Hardware Encoding](06-hardware-encoding.md)**
