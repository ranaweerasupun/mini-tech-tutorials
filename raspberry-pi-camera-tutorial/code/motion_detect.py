"""
motion_detect.py
----------------
Detects motion using frame differencing and saves a photo when triggered.

How it works:
  1. Capture the current frame as a numpy array.
  2. Subtract the previous frame from it, pixel by pixel.
  3. Count how many pixels changed by more than MOTION_THRESHOLD.
  4. If the count exceeds MOTION_MIN_PIXELS, declare motion detected.

Tuning tips:
  - MOTION_THRESHOLD: how different a pixel needs to be to count as 'changed'.
    Too low → false triggers from sensor noise and subtle lighting shifts.
    Too high → misses real motion. Start at 25 and adjust.

  - MOTION_MIN_PIXELS: how many changed pixels trigger an alert.
    Small value → sensitive (detects even small objects / insects).
    Large value → only large movement triggers it (whole-person movement).
    A good starting point is 1-2% of total pixels (e.g. 5000 for 640×480).

  - CAPTURE_INTERVAL: how often to compare frames (in seconds).
    Shorter = more responsive but higher CPU usage.
    0.1s (10 fps equivalent) is a good balance for most use cases.

Run: python3 motion_detect.py
"""

from picamera2 import Picamera2
import numpy as np
import time
import os

# -----------------------------------------------------------------------
# Configuration — tune these for your environment
# -----------------------------------------------------------------------
MOTION_THRESHOLD  = 25       # Per-pixel change to count as 'moved'
MOTION_MIN_PIXELS = 5000     # Minimum changed pixels to trigger
CAPTURE_INTERVAL  = 0.1      # Seconds between frame comparisons
COOLDOWN_SECONDS  = 3        # Seconds to wait after a trigger before re-arming
OUTPUT_DIR        = "motion_captures"
# -----------------------------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

picam2 = Picamera2()

# Use a low-resolution video configuration for speed.
# We don't need high resolution for detecting movement —
# 640×480 is plenty and keeps CPU usage low.
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()

print("Warming up...")
time.sleep(2)

# Capture the first reference frame. We cast to int16 immediately because
# when we subtract two uint8 arrays, negative results would wrap around
# to large positive values (e.g. 0 - 1 = 255), giving false positives.
previous_frame = picam2.capture_array().astype(np.int16)

last_trigger_time = 0
total_triggers = 0

print(f"Motion detector active. Saving events to '{OUTPUT_DIR}/'")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        current_frame = picam2.capture_array().astype(np.int16)

        # Absolute difference: how much did each pixel change?
        diff = np.abs(current_frame - previous_frame)

        # Count pixels where at least one colour channel changed significantly.
        # np.max(..., axis=2) collapses the 3 colour channels into one value
        # per pixel — the largest single-channel change at that position.
        max_channel_diff = np.max(diff, axis=2)
        changed_pixels = int(np.sum(max_channel_diff > MOTION_THRESHOLD))

        now = time.time()
        in_cooldown = (now - last_trigger_time) < COOLDOWN_SECONDS

        if changed_pixels > MOTION_MIN_PIXELS and not in_cooldown:
            last_trigger_time = now
            total_triggers += 1

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            filename  = os.path.join(
                OUTPUT_DIR,
                f"motion_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
            )
            picam2.capture_file(filename)
            print(f"[{timestamp}] MOTION DETECTED — "
                  f"{changed_pixels:,} changed pixels → {filename}")

        # Roll the current frame forward to become the next comparison baseline
        previous_frame = current_frame

        time.sleep(CAPTURE_INTERVAL)

except KeyboardInterrupt:
    picam2.stop()
    print(f"\nDetector stopped. {total_triggers} event(s) recorded.")
