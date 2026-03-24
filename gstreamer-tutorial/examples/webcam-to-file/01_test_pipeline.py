"""
01_test_pipeline.py
-------------------
The absolute minimum GStreamer script: open a camera and verify
it produces frames. Nothing is saved to disk. This is purely
a hardware and configuration sanity check.

Run this first before any of the other scripts. If this does not
work, something is wrong at the hardware or driver level and the
other scripts will not work either.

Run:    python3 01_test_pipeline.py
Stop:   Ctrl+C

Expected outcome:
  If you have a display connected: a window appears showing the live
  camera feed. Ctrl+C stops it cleanly.

  If you are running headlessly (SSH, no monitor): the script runs
  silently with no visible output other than the "Recording..." line.
  Frame data is being read and discarded by fakesink. Ctrl+C stops it.
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import signal
import sys
import time

# Initialise the GStreamer library. This must be called before any
# other GStreamer function. Pass sys.argv to let GStreamer consume
# any GStreamer-specific command-line arguments, or None to ignore them.
Gst.init(None)

# -----------------------------------------------------------------
# Build the pipeline
# -----------------------------------------------------------------
# We use parse_launch here because the pipeline is simple and fixed.
# The pipeline string is identical to what you would type in gst-launch-1.0,
# which makes it easy to test changes in the terminal first.
#
# Change /dev/video0 if your camera is at a different device path.
# Check available devices with: v4l2-ctl --list-devices
#
# autovideosink opens a display window if one is available.
# If you are working headlessly, replace it with fakesink.

pipeline = Gst.parse_launch("""
    v4l2src device=/dev/video0
    ! image/jpeg,width=1280,height=720,framerate=30/1
    ! jpegdec
    ! videoconvert
    ! autovideosink
""")

# -----------------------------------------------------------------
# State management
# -----------------------------------------------------------------
# set_state returns immediately — it does not wait for the pipeline
# to actually reach the PLAYING state. The transition happens
# asynchronously. For this simple test script that is fine; for
# scripts that need to know when the pipeline is fully ready before
# doing something, you would wait on a state-change message from
# the bus.
pipeline.set_state(Gst.State.PLAYING)

# -----------------------------------------------------------------
# Graceful shutdown on Ctrl+C
# -----------------------------------------------------------------
def on_sigint(sig, frame):
    """
    This function is called when the user presses Ctrl+C.
    Transitioning to NULL releases the camera device and closes
    any open display windows cleanly, rather than leaving them
    in an undefined state.
    """
    print("\nStopping pipeline...")
    pipeline.set_state(Gst.State.NULL)
    sys.exit(0)

signal.signal(signal.SIGINT, on_sigint)

# -----------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------
# Poll the GStreamer message bus for errors while the pipeline runs.
# If GStreamer reports an error (camera disconnected, driver crash, etc.)
# we print the message and stop cleanly rather than hanging forever.
bus = pipeline.get_bus()

print("Pipeline running. Press Ctrl+C to stop.")

while True:
    # timed_pop_filtered checks for a message without blocking.
    # timeout=0 means return immediately if no message is waiting.
    msg = bus.timed_pop_filtered(
        Gst.MSECOND * 100,                  # check every 100ms
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    if msg is not None:
        if msg.type == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            print(f"\nGStreamer error: {err.message}")
            print(f"Debug info:      {debug_info}")
            break
        elif msg.type == Gst.MessageType.EOS:
            # End-of-stream from a live camera is unexpected — it usually
            # means the camera was physically disconnected.
            print("\nEnd of stream (camera disconnected?)")
            break

pipeline.set_state(Gst.State.NULL)
print("Pipeline stopped.")
