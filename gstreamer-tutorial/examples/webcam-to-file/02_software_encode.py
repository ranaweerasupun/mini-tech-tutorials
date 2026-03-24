"""
02_software_encode.py
---------------------
Captures 720p30 video from a USB webcam and saves it to an MP4 file
using x264 software encoding (CPU-based H.264 compression).

This is the BASELINE script. Run it and observe the CPU usage in htop.
Then run 03_hardware_encode.py and compare. The pipeline logic is
identical — only the encoder and one converter change.

Run:    python3 02_software_encode.py
Stop:   Ctrl+C   (important: always use Ctrl+C, not kill -9, to ensure
                  the MP4 file is written correctly — see note below)

Output: output_software.mp4 in the current directory

CPU usage expectation: 60–80% on one core (almost all from x264enc).
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import signal
import sys
import time

Gst.init(None)

# -----------------------------------------------------------------
# Pipeline: webcam → decode → convert → encode → mux → file
# -----------------------------------------------------------------
#
# Reading left to right, here is what each step does:
#
#   v4l2src          Opens the camera and streams MJPEG-compressed frames.
#
#   image/jpeg,...   Caps filter: demand exactly this resolution and
#                    framerate. Without it, the camera might default to
#                    a lower resolution or different framerate.
#
#   jpegdec          Decompresses each MJPEG frame into raw pixel data.
#                    The H.264 encoder cannot accept compressed input —
#                    it needs raw frames to work with.
#
#   videoconvert     Converts the raw frame's pixel format to whatever
#                    x264enc expects. Format negotiation is automatic.
#
#   x264enc          The software H.264 encoder. Runs entirely on the CPU.
#                    tune=zerolatency  → encodes each frame as quickly as
#                                        possible without buffering ahead.
#                    speed-preset=ultrafast → fastest CPU-mode at the cost
#                                        of slightly larger output files.
#                    bitrate=2000      → target 2 Mbps output (kbps units).
#
#   h264parse        Parses and reorganises the H.264 stream.
#                    config-interval=1 → embeds stream headers with every
#                                        keyframe so players can seek freely.
#
#   mp4mux           Wraps the H.264 stream in an MP4 container, adding
#                    timestamps, seeking tables, and metadata. Without a
#                    container, the raw H.264 stream is harder to work with.
#
#   filesink         Writes the MP4 byte stream to disk.
#                    sync=false        → do not throttle writing to real-time;
#                                        write as fast as the disk allows.

pipeline = Gst.parse_launch("""
    v4l2src device=/dev/video0
    ! image/jpeg,width=1280,height=720,framerate=30/1
    ! jpegdec
    ! videoconvert
    ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000
    ! h264parse config-interval=1
    ! mp4mux
    ! filesink location=output_software.mp4 sync=false
""")

# -----------------------------------------------------------------
# Graceful shutdown
# -----------------------------------------------------------------
# WHY THIS MATTERS: mp4mux writes its index (the moov atom, which tells
# media players where each frame is in the file) at the very end of
# the file, when it receives an EOS (end-of-stream) signal. If the
# process is killed without sending EOS first, the moov atom is never
# written and the output file will not open in most media players.
#
# The correct shutdown sequence is:
#   1. Send EOS into the pipeline (pipeline.send_event)
#   2. Wait for the EOS message to propagate to the sink
#   3. Then transition to NULL state
#
# Ctrl+C triggers SIGINT, which we handle below to do this correctly.

def on_sigint(sig, frame):
    print("\nStopping... sending EOS to finalise the MP4 file.")
    # Sending EOS propagates a signal downstream through the pipeline.
    # When it reaches mp4mux, it writes the index and closes the file
    # properly. We then wait for the EOS message on the bus to confirm
    # completion before transitioning to NULL.
    pipeline.send_event(Gst.Event.new_eos())
    # (The bus polling loop below will handle the rest of the shutdown.)

signal.signal(signal.SIGINT, on_sigint)

# -----------------------------------------------------------------
# Start recording
# -----------------------------------------------------------------
pipeline.set_state(Gst.State.PLAYING)
print("Recording with SOFTWARE encoder (x264).")
print("Check CPU usage in htop — expect ~60-80% on one core.")
print("Output: output_software.mp4")
print("Press Ctrl+C to stop and finalise the file.\n")

# -----------------------------------------------------------------
# Bus polling loop
# -----------------------------------------------------------------
bus = pipeline.get_bus()

while True:
    msg = bus.timed_pop_filtered(
        Gst.MSECOND * 200,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    if msg is not None:
        if msg.type == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            print(f"\nGStreamer error: {err.message}")
            print(f"Debug info:      {debug_info}")
            break

        elif msg.type == Gst.MessageType.EOS:
            # EOS has propagated all the way to the sink, meaning
            # mp4mux has finished writing and filesink has closed.
            print("File finalised successfully.")
            break

pipeline.set_state(Gst.State.NULL)
print("Pipeline stopped. Output saved to: output_software.mp4")
