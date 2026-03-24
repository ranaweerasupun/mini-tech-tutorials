"""
first_camera.py
---------------
The absolute minimum camera script. Starts the camera, waits for
auto-exposure to settle, captures one image, then shuts down cleanly.

Run: python3 first_camera.py
"""

from picamera2 import Picamera2
import time

# Create the camera object. No hardware activity yet — this is
# just setting up the Python-side connection to the camera system.
picam2 = Picamera2()

# Start the camera. The sensor powers up and begins streaming frames
# continuously in the background.
picam2.start()

# Wait for the automatic exposure and white balance algorithms to
# analyse the scene and converge on stable settings. Without this
# pause, the first captured frame is often poorly exposed.
time.sleep(2)

# Grab the current frame and save it. The camera has been running
# this whole time, so the capture is nearly instantaneous.
picam2.capture_file("test.jpg")

# Shut the camera down and release the hardware resources.
picam2.stop()

print("Done! Open test.jpg to see the result.")
