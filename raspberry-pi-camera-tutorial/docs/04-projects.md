# 04 — Practical Projects

This document takes everything from the previous sections and puts it to work. Each project is self-contained, progressively builds on earlier concepts, and is designed to be genuinely useful rather than just a demonstration. All the complete, ready-to-run scripts live in the [`code/`](../code/) folder.

---

## Project 1: Automated Time-Lapse

A time-lapse is one of the most satisfying camera projects because the result is immediately visual and rewarding. The idea is simple: capture a photo at a regular interval and then stitch those frames together into a video that compresses hours of change into seconds of footage.

The key insight for writing a good time-lapse script is that the camera should stay running the whole time. Starting and stopping the camera between captures would mean waiting for auto-exposure to re-settle every single time, which would produce flickering and inconsistency between frames. Instead, you start once, let the auto-exposure stabilize, and then capture on a schedule.

Here's the complete time-lapse script. See [`code/timelapse.py`](../code/timelapse.py) for the full version with keyboard interrupt handling.

```python
from picamera2 import Picamera2
import time
import os

# --- Configuration ---
INTERVAL_SECONDS = 10     # How often to capture a frame
TOTAL_CAPTURES   = 360    # Total number of frames (360 × 10s = 1 hour)
OUTPUT_DIR       = "timelapse_frames"
# ---------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)

picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
picam2.start()

print("Warming up auto-exposure...")
time.sleep(2)
print(f"Starting time-lapse: {TOTAL_CAPTURES} frames at {INTERVAL_SECONDS}s intervals")

for i in range(TOTAL_CAPTURES):
    filename = os.path.join(OUTPUT_DIR, f"frame_{i:04d}.jpg")
    picam2.capture_file(filename)
    print(f"[{i+1}/{TOTAL_CAPTURES}] Saved {filename}")
    time.sleep(INTERVAL_SECONDS)

picam2.stop()
print("Time-lapse capture complete!")
print(f"Frames saved to: {OUTPUT_DIR}/")
print("To assemble into a video, run:")
print("  ffmpeg -r 24 -i timelapse_frames/frame_%04d.jpg -c:v libx264 timelapse.mp4")
```

Once you have your frames, assemble them into a video with `ffmpeg`. The `-r 24` flag sets the output frame rate to 24 frames per second, so if you captured a frame every 10 seconds over one hour, the resulting video will be 15 seconds long (360 frames ÷ 24 fps). Adjust the frame rate to taste — a lower value makes the time-lapse feel slower and more contemplative, a higher value makes it feel faster.

---

## Project 2: Button-Triggered Capture

This project connects a physical push button to the Pi's GPIO pins so that pressing the button takes a photo. It's a great introduction to combining camera control with hardware interaction, and it's the foundation for building dedicated camera devices like photo booths or wildlife trap cameras.

You'll need a push button, a 10kΩ resistor (for the pull-down), and three short jumper wires. Connect one end of the button to 3.3V (Pin 1), the other end to your chosen GPIO pin (this example uses GPIO 17, which is Pin 11), and a 10kΩ resistor between the GPIO pin and GND (Pin 6). With this wiring, the GPIO pin reads LOW normally and HIGH when the button is pressed.

```python
from picamera2 import Picamera2
from gpiozero import Button    # pip install gpiozero if needed
import time
import signal
import sys

BUTTON_GPIO_PIN = 17

picam2 = Picamera2()
picam2.start()
time.sleep(2)  # Auto-exposure warm-up

button = Button(BUTTON_GPIO_PIN, pull_up=False)

photo_count = 0

def take_photo():
    global photo_count
    photo_count += 1
    filename = f"capture_{photo_count:04d}.jpg"
    picam2.capture_file(filename)
    print(f"📷 Saved {filename}")

# Assign the function to the button's press event
button.when_pressed = take_photo

print("Camera ready. Press the button to take a photo. Ctrl+C to quit.")

# Keep the script running until the user presses Ctrl+C
try:
    signal.pause()
except KeyboardInterrupt:
    picam2.stop()
    print(f"\nDone. {photo_count} photo(s) taken.")
    sys.exit(0)
```

The `gpiozero` library's `when_pressed` callback pattern is used here because it's far simpler than manually polling the GPIO pin in a loop. When the button is pressed, `gpiozero` detects the rising edge and calls `take_photo()` automatically, even while the main thread is sitting quietly in `signal.pause()`. This event-driven approach is much more efficient and responsive than a polling loop.

---

## Project 3: Simple Motion Detection

Motion detection using a camera is surprisingly straightforward at a basic level. The principle is **frame differencing**: capture two consecutive frames, subtract one from the other pixel by pixel, and if enough pixels show a large difference, something in the scene must have moved. When nothing is moving, consecutive frames should be nearly identical, so the difference will be close to zero everywhere.

```python
from picamera2 import Picamera2
import numpy as np
import time

# Tune these to your environment
MOTION_THRESHOLD  = 25     # Pixel difference needed to count as 'changed'
MOTION_MIN_PIXELS = 5000   # Minimum number of changed pixels to trigger alert

picam2 = Picamera2()

# Use a low-resolution config for speed — we don't need detail for detection
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)

print("Motion detector active. Press Ctrl+C to stop.")

# Capture the initial reference frame
previous_frame = picam2.capture_array().astype(np.int16)

try:
    while True:
        current_frame = picam2.capture_array().astype(np.int16)

        # Compute the absolute difference between frames
        # We cast to int16 first to avoid unsigned integer underflow
        diff = np.abs(current_frame - previous_frame)

        # Count how many pixels changed significantly
        changed_pixels = np.sum(diff > MOTION_THRESHOLD)

        if changed_pixels > MOTION_MIN_PIXELS:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            filename  = f"motion_{time.strftime('%Y%m%d_%H%M%S')}.jpg"

            # Save the current frame as evidence of the motion event
            picam2.capture_file(filename)
            print(f"[{timestamp}] MOTION DETECTED — {changed_pixels} changed pixels → {filename}")

        # The current frame becomes the reference for the next comparison
        previous_frame = current_frame

        # Small pause to reduce CPU usage; adjust based on your needs
        time.sleep(0.1)

except KeyboardInterrupt:
    picam2.stop()
    print("Motion detector stopped.")
```

A few practical notes on tuning this script. `MOTION_THRESHOLD` controls how different a pixel needs to be to count as changed. Set it too low and you'll get false triggers from sensor noise and subtle lighting shifts; set it too high and you'll miss subtle movements. A value between 20 and 40 works well in typical indoor lighting. `MOTION_MIN_PIXELS` controls how many pixels need to change before you declare it a motion event. A large threshold here filters out small insects, swaying plants, or brief lighting changes that affect only a small part of the frame. Adjust it based on the physical size of what you want to detect relative to your camera's resolution.

---

## Project 4: Video Recording with Start/Stop

Recording video to a file is handled by the encoder system described in the architecture section. This project wraps that into a clean script where you press Enter to toggle recording on and off.

```python
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import time

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration())
picam2.start()
time.sleep(2)

encoder = H264Encoder(bitrate=10_000_000)  # 10 Mbps — good quality
recording = False
clip_count = 0

print("Press Enter to start/stop recording. Type 'quit' to exit.")

while True:
    user_input = input("● " if recording else "○ ")

    if user_input.lower() == "quit":
        if recording:
            picam2.stop_encoder()
        break

    if not recording:
        clip_count += 1
        filename = f"clip_{clip_count:03d}.h264"
        picam2.start_encoder(encoder, FileOutput(filename))
        recording = True
        print(f"Recording → {filename} (press Enter to stop)")
    else:
        picam2.stop_encoder()
        recording = False
        print(f"Stopped. Clip saved.")

picam2.stop()
print("Done.")
print("To convert .h264 to .mp4, run:")
print("  ffmpeg -i clip_001.h264 -c copy clip_001.mp4")
```

The H.264 files that Picamera2 produces are raw H.264 bitstreams, not MP4 containers. They'll play in VLC, but they don't have timestamps embedded. The `ffmpeg` command at the end wraps them in an MP4 container without re-encoding, which is essentially instant and preserves the full quality.

If you'd like a proper `.mp4` file directly without the conversion step, you can use `FfmpegOutput` instead of `FileOutput`:

```python
from picamera2.outputs import FfmpegOutput

# This produces a properly containerised MP4 directly
picam2.start_encoder(encoder, FfmpegOutput("clip.mp4"))
```

This requires `ffmpeg` to be installed (`sudo apt install ffmpeg`), and it's a little slower to start because `ffmpeg` itself needs to launch, but the output is a complete, properly-formed MP4 file.

---

## Going Further

These four projects cover the most common patterns: scheduled automation, hardware-triggered events, image analysis, and video recording. But they're all starting points, not endpoints. Some directions you might explore next include combining motion detection with video recording (save a clip when motion is detected and stop after a quiet period), adding timestamps or annotations to images using PIL's drawing functions, streaming video over a network with `FfmpegOutput` and an RTSP target, or integrating with computer vision libraries like OpenCV for face or object detection.

**Next: [05 — Troubleshooting](05-troubleshooting.md)**
