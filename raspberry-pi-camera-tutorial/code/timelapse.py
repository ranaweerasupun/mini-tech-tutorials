"""
timelapse.py
------------
Captures frames at a regular interval for assembling into a time-lapse video.
The camera stays running the whole time so auto-exposure remains stable
and frames are consistent — no flicker from per-capture startup.

After capturing, use ffmpeg to assemble frames into a video:
  ffmpeg -r 24 -i timelapse_frames/frame_%04d.jpg -c:v libx264 timelapse.mp4

Adjust -r to change playback speed:
  -r 24  → 24 fps (360 frames = 15 second video)
  -r 12  → 12 fps (360 frames = 30 second video, slower / more contemplative)

Run: python3 timelapse.py
"""

from picamera2 import Picamera2
import time
import os

# -----------------------------------------------------------------------
# Configuration — adjust these values to suit your project
# -----------------------------------------------------------------------
INTERVAL_SECONDS = 10      # Time between captures in seconds
TOTAL_CAPTURES   = 360     # Total number of frames (360 × 10s = 1 hour of real time)
OUTPUT_DIR       = "timelapse_frames"
# -----------------------------------------------------------------------

# Create the output directory if it doesn't already exist.
# exist_ok=True means no error if the folder is already there.
os.makedirs(OUTPUT_DIR, exist_ok=True)

picam2 = Picamera2()

# Still configuration maximises quality. For long time-lapses outdoors,
# this gives you frames that hold up well in the assembled video.
picam2.configure(picam2.create_still_configuration())
picam2.start()

print("Warming up auto-exposure (2 seconds)...")
time.sleep(2)

total_duration_minutes = (TOTAL_CAPTURES * INTERVAL_SECONDS) / 60
print(f"Starting time-lapse: {TOTAL_CAPTURES} frames × {INTERVAL_SECONDS}s = "
      f"{total_duration_minutes:.0f} minutes of real time\n")

start_time = time.time()

try:
    for i in range(TOTAL_CAPTURES):
        # :04d pads with leading zeros to 4 digits, ensuring frames sort
        # correctly: frame_0001.jpg, ..., frame_0360.jpg
        filename = os.path.join(OUTPUT_DIR, f"frame_{i + 1:04d}.jpg")

        capture_start = time.time()
        picam2.capture_file(filename)
        capture_time = time.time() - capture_start

        elapsed = time.time() - start_time
        remaining = (TOTAL_CAPTURES - i - 1) * INTERVAL_SECONDS
        print(f"  [{i + 1:>4}/{TOTAL_CAPTURES}] {filename}  "
              f"(captured in {capture_time:.2f}s, "
              f"~{remaining // 60:.0f}m remaining)")

        # Sleep for the remainder of the interval, accounting for capture time.
        # This keeps the interval accurate even if capture takes a moment.
        sleep_time = INTERVAL_SECONDS - capture_time
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    # If the user presses Ctrl+C, finish cleanly rather than crashing.
    print("\n\nInterrupted by user. Saving what we have...")

finally:
    picam2.stop()

    # Count how many frames were actually saved
    saved_count = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".jpg")])
    print(f"\nCapture complete: {saved_count} frame(s) saved to '{OUTPUT_DIR}/'")
    print("\nTo assemble into a video:")
    print(f"  ffmpeg -r 24 -i {OUTPUT_DIR}/frame_%04d.jpg -c:v libx264 timelapse.mp4")
