"""
video_record.py
---------------
Records H.264 video clips with interactive start/stop control.
Press Enter to toggle recording. Type 'quit' to exit.

The .h264 files produced are raw H.264 bitstreams. They play in VLC
but don't have timestamps embedded. Convert to proper .mp4 with:

  ffmpeg -i clip_001.h264 -c copy clip_001.mp4

If you'd prefer to record directly to .mp4 without a conversion step,
see the FfmpegOutput example at the bottom of this file.

Run: python3 video_record.py
"""

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import time

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
BITRATE = 10_000_000    # 10 Mbps — good balance of quality and file size.
                         # Increase for less compression artefacts,
                         # decrease to save disk space.
# -----------------------------------------------------------------------

picam2 = Picamera2()

# Video configuration selects a sensor mode optimised for continuous
# frame delivery — lower resolution than still but higher frame rate.
picam2.configure(picam2.create_video_configuration())

# Create the encoder once. It can be started and stopped multiple times.
encoder = H264Encoder(bitrate=BITRATE)

picam2.start()
time.sleep(2)

recording = False
clip_count = 0

print("Video recorder ready.")
print("Press Enter to start recording, Enter again to stop.")
print("Type 'quit' to exit.\n")

while True:
    # The ● and ○ indicators in the prompt give a clear visual cue
    # about whether the camera is actively recording or standing by.
    indicator = "● REC" if recording else "○ STANDBY"
    user_input = input(f"[{indicator}] → ")

    if user_input.lower() == "quit":
        if recording:
            picam2.stop_encoder()
            print("Recording stopped.")
        break

    if not recording:
        # Start a new clip
        clip_count += 1
        filename = f"clip_{clip_count:03d}.h264"
        picam2.start_encoder(encoder, FileOutput(filename))
        recording = True
        print(f"  Recording → {filename}  (press Enter to stop)")

    else:
        # Stop the current clip
        picam2.stop_encoder()
        recording = False
        print(f"  Clip saved.\n")

picam2.stop()
print(f"\nSession ended. {clip_count} clip(s) recorded.")
if clip_count > 0:
    print("To convert to .mp4 (no re-encoding, instant):")
    for i in range(1, clip_count + 1):
        print(f"  ffmpeg -i clip_{i:03d}.h264 -c copy clip_{i:03d}.mp4")


# -----------------------------------------------------------------------
# ALTERNATIVE: Record directly to .mp4 using FfmpegOutput
# -----------------------------------------------------------------------
# If you prefer .mp4 output without a post-processing step, replace
# the FileOutput line with FfmpegOutput. This requires ffmpeg installed:
#   sudo apt install ffmpeg
#
# from picamera2.outputs import FfmpegOutput
# picam2.start_encoder(encoder, FfmpegOutput("clip.mp4"))
#
# FfmpegOutput is slightly slower to start because it launches ffmpeg
# as a subprocess, but the output is a fully-formed, timestamped .mp4.
# -----------------------------------------------------------------------
