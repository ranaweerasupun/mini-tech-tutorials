"""
03_hardware_encode.py
---------------------
Captures 720p30 video from a USB webcam and saves it to an MP4 file
using the Raspberry Pi 5's built-in VideoCore hardware H.264 encoder.

This script is functionally identical to 02_software_encode.py — same
resolution, same output format, same controls — but replaces the software
x264 encoder with the hardware v4l2h264enc encoder. The result is the
same output file with roughly 60-65% less CPU usage.

Run:    python3 03_hardware_encode.py
Stop:   Ctrl+C

Output: output_hardware.mp4 in the current directory

CPU usage expectation: ~15-25% total (vs 60-80% with software encoding).

NOTE: This script is specific to the Raspberry Pi 5. The v4l2h264enc
element relies on the VideoCore VII hardware encoder block that is present
in the BCM2712 chip. It will not work on other Linux systems unless they
have their own V4L2 hardware encoder (and even then, may need adjustment).
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import signal
import subprocess
import sys

Gst.init(None)


def set_encoder_bitrate(bitrate_bps: int) -> None:
    """
    Set the hardware encoder's target bitrate using v4l2-ctl.

    The v4l2h264enc GStreamer element does not expose bitrate as a standard
    GStreamer property. Instead, the hardware encoder is configured through
    V4L2 kernel controls, which v4l2-ctl can set directly.

    We call this before the pipeline starts so the bitrate is already
    configured when the encoder element opens the hardware device.

    Args:
        bitrate_bps: Target bitrate in bits per second (e.g. 2000000 = 2 Mbps)
    """
    # Find the encoder device. The hardware codec shows up as a V4L2 device
    # but we need the specific /dev/videoN number that corresponds to the
    # encoder function (not the camera, not the decoder).
    result = subprocess.run(
        ["v4l2-ctl", "--list-devices"],
        capture_output=True, text=True
    )

    encoder_device = None
    lines = result.stdout.splitlines()
    in_codec_section = False

    for line in lines:
        # The hardware codec section is headed by 'bcm2835-codec'
        if "bcm2835-codec" in line:
            in_codec_section = True
            continue
        # The first device listed under bcm2835-codec is the encoder
        if in_codec_section and "/dev/video" in line:
            encoder_device = line.strip()
            break
        # An empty line means we have left the codec section
        if in_codec_section and line.strip() == "":
            break

    if encoder_device is None:
        print("WARNING: Could not find hardware encoder device.")
        print("         The pipeline will use the encoder's default bitrate.")
        print("         Run 'v4l2-ctl --list-devices' to check availability.")
        return

    subprocess.run(
        ["v4l2-ctl", "-d", encoder_device,
         "--set-ctrl", f"video_bitrate={bitrate_bps}"],
        check=False  # Don't raise an exception if this fails; the pipeline will still run
    )
    print(f"Set hardware encoder bitrate: {bitrate_bps // 1000} kbps on {encoder_device}")


# -----------------------------------------------------------------
# Set bitrate before building the pipeline
# -----------------------------------------------------------------
set_encoder_bitrate(2_000_000)   # 2 Mbps — same as the software example

# -----------------------------------------------------------------
# Pipeline: webcam → decode → v4l2convert → hardware encoder → mux → file
# -----------------------------------------------------------------
#
# Compare this carefully with 02_software_encode.py. Three things changed:
#
#   videoconvert  →  v4l2convert
#   (new)            video/x-raw,format=I420  [caps filter]
#   x264enc       →  v4l2h264enc extra-controls="controls,repeat_sequence_header=1,h264_i_frame_period=30"
#   (new)            video/x-h264,level=(string)4  [caps filter]
#
# Everything else is identical. See docs/06-hardware-encoding.md for a
# detailed explanation of why each of these specific changes is necessary.

pipeline = Gst.parse_launch("""
    v4l2src device=/dev/video0
    ! image/jpeg,width=1280,height=720,framerate=30/1
    ! jpegdec

    ! v4l2convert
    ! video/x-raw,format=I420

    ! v4l2h264enc extra-controls="controls,repeat_sequence_header=1,h264_i_frame_period=30"
    ! video/x-h264,level=(string)4

    ! h264parse config-interval=1
    ! mp4mux
    ! filesink location=output_hardware.mp4 sync=false
""")

# -----------------------------------------------------------------
# Graceful shutdown (identical reason as in 02_software_encode.py:
# mp4mux needs an EOS signal to write the file index correctly)
# -----------------------------------------------------------------
def on_sigint(sig, frame):
    print("\nStopping... sending EOS to finalise the MP4 file.")
    pipeline.send_event(Gst.Event.new_eos())

signal.signal(signal.SIGINT, on_sigint)

# -----------------------------------------------------------------
# Start recording
# -----------------------------------------------------------------
pipeline.set_state(Gst.State.PLAYING)
print("Recording with HARDWARE encoder (v4l2h264enc).")
print("Check CPU usage in htop — expect ~15-25% total.")
print("Output: output_hardware.mp4")
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
            print("\nSee docs/07-troubleshooting.md for help decoding this error.")
            break

        elif msg.type == Gst.MessageType.EOS:
            print("File finalised successfully.")
            break

pipeline.set_state(Gst.State.NULL)
print("Pipeline stopped. Output saved to: output_hardware.mp4")
