"""
camera_settings.py
------------------
Demonstrates runtime camera controls: Brightness, Contrast, and Saturation.
Captures four images with different settings so you can compare the effects.

Controls work differently from configuration — they can be changed while
the camera is running and take effect on the live stream immediately.
A short sleep after each set_controls() call lets the change propagate
through the pipeline before the next capture.

Run: python3 camera_settings.py
"""

from picamera2 import Picamera2
import time

picam2 = Picamera2()

# Use still configuration for maximum image quality
config = picam2.create_still_configuration()
picam2.configure(config)

picam2.start()
time.sleep(2)  # Auto-exposure warm-up

# --- 1. Baseline capture with all defaults (auto everything) ---
picam2.capture_file("1_normal.jpg")
print("Saved 1_normal.jpg  (default settings)")

# --- 2. Increased brightness ---
# Brightness is a post-processing offset: -1.0 (black) → 0.0 (normal) → 1.0 (white)
# It does NOT change the sensor exposure — it's applied by the ISP after capture.
picam2.set_controls({"Brightness": 0.3})
time.sleep(1)
picam2.capture_file("2_bright.jpg")
print("Saved 2_bright.jpg  (Brightness +0.3)")

# --- 3. High contrast (reset brightness first) ---
# Contrast affects how far apart the shadows and highlights are.
# 1.0 = normal, higher values = more dramatic, lower = flat/washed out.
picam2.set_controls({"Brightness": 0.0, "Contrast": 1.8})
time.sleep(1)
picam2.capture_file("3_contrast.jpg")
print("Saved 3_contrast.jpg  (Contrast 1.8)")

# --- 4. Vivid saturation ---
# Saturation controls color intensity.
# 1.0 = natural, 0.0 = grayscale, values above 1.0 = increasingly vivid.
picam2.set_controls({"Contrast": 1.0, "Saturation": 2.0})
time.sleep(1)
picam2.capture_file("4_saturated.jpg")
print("Saved 4_saturated.jpg  (Saturation 2.0)")

picam2.stop()
print("\nDone! Compare the four images to see the effect of each control.")
print("Tip: open them side-by-side with:  eog *.jpg")
