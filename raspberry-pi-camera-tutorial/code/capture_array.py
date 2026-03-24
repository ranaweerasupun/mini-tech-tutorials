"""
capture_array.py
----------------
Captures an image directly into a NumPy array instead of saving to a file.
This is the gateway to computer vision — once you have the image as an
array, you can analyse every pixel in Python.

This script captures a frame, inspects its structure, calculates some basic
statistics, makes a simple decision based on brightness, then saves the
array as a JPEG to confirm it looks correct.

Run: python3 capture_array.py
"""

from picamera2 import Picamera2
from PIL import Image
import numpy as np
import time

picam2 = Picamera2()

# RGB888 format gives us clean 3-channel RGB with no alpha channel,
# which is the most convenient format for numpy-based processing.
config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"}
)
picam2.configure(config)
picam2.start()
time.sleep(2)

# capture_array() returns a numpy ndarray instead of saving to disk.
# The camera is already streaming, so this grabs the latest available frame.
image_array = picam2.capture_array()

# --- Inspect the array structure ---
print("=== Image Array Structure ===")
print(f"  Shape:     {image_array.shape}")     # (height, width, channels)
print(f"  Data type: {image_array.dtype}")      # uint8 = values 0-255
print(f"  Min value: {image_array.min()}")      # 0 = black
print(f"  Max value: {image_array.max()}")      # 255 = max brightness

# --- Basic statistics ---
# .mean() across the whole array gives average brightness across all pixels
# and all three colour channels combined.
avg_brightness = image_array.mean()
print(f"\n=== Brightness Analysis ===")
print(f"  Overall average pixel value: {avg_brightness:.1f} / 255")

# We can also look at each colour channel independently by slicing the
# third dimension. Index 0 = Red, 1 = Green, 2 = Blue.
r_mean = image_array[:, :, 0].mean()
g_mean = image_array[:, :, 1].mean()
b_mean = image_array[:, :, 2].mean()
print(f"  Red channel average:   {r_mean:.1f}")
print(f"  Green channel average: {g_mean:.1f}")
print(f"  Blue channel average:  {b_mean:.1f}")

# --- Make a decision based on pixel data ---
# This is a tiny example of what becomes motion detection, face recognition,
# object classification, etc. — you just have more sophisticated logic.
print(f"\n=== Scene Assessment ===")
if avg_brightness < 60:
    print("  Scene is quite dark — consider increasing lighting or exposure.")
elif avg_brightness > 200:
    print("  Scene is very bright — consider reducing exposure.")
else:
    print("  Scene brightness looks reasonable.")

# --- Save the array back to disk to visually confirm it looks right ---
img = Image.fromarray(image_array)
img.save("array_capture.jpg")
print("\n  Saved array_capture.jpg for visual confirmation.")

picam2.stop()
print("\nDone! The image array is ready for any further processing you need.")
