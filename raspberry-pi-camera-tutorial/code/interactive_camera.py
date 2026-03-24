"""
interactive_camera.py
---------------------
An interactive photo booth. The camera starts once and stays running,
so each capture is instant. Press Enter to shoot, type 'quit' to exit.

This demonstrates a key principle: keeping the camera warm between
captures gives you much faster and more consistent results than
starting it fresh for each shot.

Run: python3 interactive_camera.py
"""

from picamera2 import Picamera2
import time

# Start the camera once and leave it running for the whole session.
# Auto-exposure settles once, and every capture after that is instant.
picam2 = Picamera2()
picam2.start()

print("Warming up camera...")
time.sleep(2)
print("Camera ready! Press Enter to take a photo, or type 'quit' to exit.\n")

photo_count = 1

while True:
    user_input = input("[ Ready ] Press Enter to capture → ")

    if user_input.lower() == "quit":
        break

    # :03d formats the number with at least 3 digits, left-padded with zeros.
    # This ensures files sort correctly in the filesystem:
    # photo_001.jpg, photo_002.jpg, ..., photo_010.jpg (not photo_1, photo_10)
    filename = f"photo_{photo_count:03d}.jpg"

    picam2.capture_file(filename)
    print(f"  ✓ Saved {filename}\n")

    photo_count += 1

# Always stop the camera to release the hardware.
picam2.stop()
print(f"Session ended. {photo_count - 1} photo(s) saved.")
