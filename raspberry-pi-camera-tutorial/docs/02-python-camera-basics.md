# 02 — Python Camera Basics

This is where things start to get genuinely interesting. When you control the camera from Python instead of the terminal, you move from running one-off commands to writing programs that can make intelligent decisions — capturing on a schedule, reacting to events, or processing what the camera sees in real time. This document walks you from your first three-line script all the way up to reading raw pixel data as a numpy array.

---

## Why Python Instead of the Command Line?

When you run `libcamera-still` from the terminal, the entire camera system starts up, captures one image, and then shuts back down. Every single time. There's a real cost to this: the startup involves loading the camera firmware, allocating memory buffers, and most importantly, running the automatic exposure and white balance algorithms long enough for them to stabilize. That process takes at least a second or two every time.

With Python and Picamera2, you start the camera **once** and keep it running for as long as you need. The auto-exposure settles once at startup, and after that, every capture is nearly instantaneous. You can also process images directly in memory — analyzing pixel data, making decisions, and never touching the disk — which is the foundation of any computer vision application.

---

## Installing Picamera2 and Dependencies

On Raspberry Pi OS Bookworm, Picamera2 is usually pre-installed, but run this command to be sure:

```bash
sudo apt install python3-picamera2 python3-numpy python3-pil
```

`numpy` is the standard Python library for working with arrays of numbers, which is how images are represented in memory. `PIL` (from the Pillow package) provides image format support — saving numpy arrays as JPEG, PNG, and other formats.

You can verify the installation worked by running Python and importing the library:

```bash
python3 -c "from picamera2 import Picamera2; print('Picamera2 ready')"
```

If you see `Picamera2 ready`, you're good to go. If you see an error, check the [Troubleshooting guide](05-troubleshooting.md).

---

## Your First Camera Script

Create a new file called `first_camera.py` and add the following code. Every line is annotated so you understand exactly what's happening:

```python
from picamera2 import Picamera2
import time

# Create a Picamera2 object — this represents your physical camera.
# No hardware activity happens yet, this is just Python setup.
picam2 = Picamera2()

# Start the camera. This powers up the sensor and begins streaming
# frames continuously in the background.
picam2.start()

# Wait 2 seconds for auto-exposure and auto-white-balance to settle.
# Without this pause, the first frame is often poorly exposed because
# the automatic algorithms haven't had time to analyze the scene yet.
time.sleep(2)

# Grab the current frame and save it to disk as a JPEG.
picam2.capture_file("test.jpg")

# Shut down the sensor and free the hardware resources.
picam2.stop()

print("Done! Check test.jpg")
```

Run it with:

```bash
python3 first_camera.py
```

The two-second sleep isn't just an arbitrary delay — it reflects something real about how cameras work. When the camera first turns on, it sees the scene for the very first time. The auto-exposure algorithm needs to analyze several frames to estimate the correct brightness, and the auto-white-balance algorithm needs to sample enough of the scene's colors to figure out the lighting temperature. Those algorithms are continuously refining their estimates, and after about two seconds they'll have converged on stable, accurate values.

---

## Keeping the Camera Running for Multiple Captures

A key insight is that you should treat the camera like a tool you pick up at the beginning of a session and put down at the end — not something you grab and release for every individual shot. This script demonstrates that with an interactive loop:

```python
from picamera2 import Picamera2
import time

picam2 = Picamera2()
picam2.start()
time.sleep(2)  # One-time warm-up

print("Camera ready! Press Enter to capture, or type 'quit' to exit.")

photo_count = 1

while True:
    user_input = input("Ready... ")

    if user_input.lower() == "quit":
        break

    # f-string with :03d pads the number with leading zeros to 3 digits,
    # so files sort correctly: photo_001.jpg, photo_002.jpg, etc.
    filename = f"photo_{photo_count:03d}.jpg"
    picam2.capture_file(filename)
    print(f"Saved {filename}")
    photo_count += 1

# Always clean up when done
picam2.stop()
print("Camera stopped.")
```

Try pressing Enter several times in quick succession. Notice how each capture is nearly instant after the first warm-up delay. That responsiveness is the direct result of keeping the camera running throughout the session.

---

## Configuring the Camera Mode

Picamera2 has three built-in configuration modes: `still`, `video`, and `preview`. Each one optimizes the camera's internal pipeline for a different purpose.

The **still configuration** maximises image quality. It selects the highest-resolution sensor mode, applies more aggressive noise reduction, and generally sacrifices speed for quality. Use this when you care about getting the best-looking image.

The **video configuration** prioritises throughput. It chooses a sensor mode that can deliver a high frame rate, reduces processing overhead to keep frames flowing smoothly, and trades a little quality for consistency. Use this whenever you're recording video or doing real-time processing where frame rate matters.

The **preview configuration** is designed for low-latency display. It runs at reduced resolution with minimal processing so the live feed feels immediate and responsive.

Here's how you explicitly create and apply a configuration:

```python
from picamera2 import Picamera2
import time

picam2 = Picamera2()

# Create a still configuration — you get this back as a dictionary-like object
# that you can inspect and modify before applying it.
config = picam2.create_still_configuration()

# Apply the configuration to the camera. This sets up the entire image
# processing pipeline according to the configuration's parameters.
# Must be called BEFORE start().
picam2.configure(config)

picam2.start()
time.sleep(2)
picam2.capture_file("high_quality.jpg")
picam2.stop()
```

If you don't call `configure()` explicitly, Picamera2 uses a sensible default configuration — which is why the simpler scripts above work fine. But for any serious application, it's good practice to be explicit about your configuration.

---

## Adjusting Camera Controls at Runtime

Controls are the real-time adjustments you can make while the camera is running. Unlike configuration (which locks in before start), controls can be changed at any moment and they take effect immediately on the live stream.

The main controls you'll use most often are described below:

**Brightness** applies a simple offset to the entire image, making it uniformly lighter or darker. It ranges from -1.0 (very dark) to 1.0 (very bright), with 0.0 being no change. Importantly, this is a post-processing adjustment — it doesn't affect the actual sensor exposure.

**Contrast** affects the range between the darkest and brightest parts of the image. A value of 1.0 is normal. Higher values make the image feel more dramatic and punchy; lower values flatten it out.

**Saturation** controls how vivid the colors are. At 1.0, colors are natural. Higher values push toward oversaturated, almost cartoon-like colors. At 0.0, you get a grayscale image.

**ExposureTime** sets how long the sensor collects light for each frame, in microseconds. Longer exposure = more light = brighter image, but moving subjects will blur. This overrides the auto-exposure algorithm entirely.

**AnalogueGain** is the camera equivalent of ISO — it amplifies the sensor's signal before digitization. Higher values brighten the image but increase noise (grain).

Here's a practical script that demonstrates each control:

```python
from picamera2 import Picamera2
import time

picam2 = Picamera2()
picam2.start()
time.sleep(2)

# Baseline capture with default (automatic) settings
picam2.capture_file("normal.jpg")
print("Saved normal.jpg — default settings")

# Increase brightness
picam2.set_controls({"Brightness": 0.3})
time.sleep(1)  # Give the pipeline time to apply the change
picam2.capture_file("bright.jpg")
print("Saved bright.jpg — brightness +0.3")

# Increase contrast (reset brightness first)
picam2.set_controls({"Brightness": 0.0, "Contrast": 1.5})
time.sleep(1)
picam2.capture_file("high_contrast.jpg")
print("Saved high_contrast.jpg — contrast 1.5")

# Vivid color saturation
picam2.set_controls({"Contrast": 1.0, "Saturation": 1.8})
time.sleep(1)
picam2.capture_file("saturated.jpg")
print("Saved saturated.jpg — saturation 1.8")

picam2.stop()
print("Done — compare the four images to see the differences.")
```

Notice that `set_controls()` takes a dictionary where you can set multiple controls at once. Any controls you don't mention are left at their current value, which is why we reset `Brightness` and `Contrast` before the next step.

The small `time.sleep(1)` after each `set_controls()` call is important. The controls don't apply to the very next frame — they propagate through the processing pipeline over a frame or two. Without the sleep, your capture might happen just before the new settings have taken full effect.

---

## Capturing Images as Numpy Arrays

Everything covered so far saves images to disk. But for computer vision, you often want to skip the disk entirely and work with the pixel data directly in Python. This is done with `capture_array()`:

```python
from picamera2 import Picamera2
import numpy as np
import time

picam2 = Picamera2()
picam2.start()
time.sleep(2)

# Instead of saving to a file, get the image as a numpy array
image_array = picam2.capture_array()

# Let's understand what we got back
print(f"Shape:     {image_array.shape}")       # e.g. (1536, 2048, 4)
print(f"Data type: {image_array.dtype}")        # usually uint8
print(f"Min value: {image_array.min()}")        # 0 = black
print(f"Max value: {image_array.max()}")        # 255 = full brightness

# Calculate the average brightness across all pixels and channels
average_brightness = image_array.mean()
print(f"Average pixel value: {average_brightness:.1f} / 255")

# Make a simple brightness decision
if average_brightness < 80:
    print("Scene is quite dark")
elif average_brightness > 180:
    print("Scene is quite bright")
else:
    print("Scene has reasonable exposure")

# Save the array back to disk using PIL if you want a file too
from PIL import Image
img = Image.fromarray(image_array)
img.save("from_array.jpg")
print("Also saved as from_array.jpg")

picam2.stop()
```

The shape `(height, width, channels)` tells you the dimensions of the image in pixels. A typical default capture from a Camera Module 3 might be `(1536, 2048, 4)`, meaning 1536 pixels tall, 2048 wide, and 4 channels per pixel. That fourth channel is an alpha (transparency) value that you can usually ignore or slice off:

```python
# Strip the alpha channel to get clean RGB
rgb_array = image_array[:, :, :3]
print(f"RGB shape: {rgb_array.shape}")  # e.g. (1536, 2048, 3)
```

Once you have a numpy array, you can do things like crop regions, compute color statistics, compare two frames for differences (motion detection), or pass the array directly into an OpenCV or TensorFlow function. This is the gateway to everything in computer vision.

---

## Summary of What You've Learned

You now know how to start and stop the camera, why the warm-up delay matters, how configuration and controls differ, how to adjust image properties at runtime, and how to capture directly into a numpy array for in-memory processing. These are the fundamental building blocks for every camera application you'll build.

In the next document, we'll look at the full architecture of the Picamera2 library so you can understand exactly what happens under the hood when you call these methods.

**Next: [03 — Picamera2 Architecture](03-picamera2-architecture.md)**
