<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 05 — Troubleshooting

Camera issues can be frustrating because the failure can happen at any of several layers — hardware, OS, drivers, or Python code. The key is isolating which layer the problem is in, because once you know where it lives, the fix is almost always straightforward.

Start at the bottom (hardware and OS) and work upward (Python). If the hardware isn't connected properly, no amount of debugging your code will help.

---

## Diagnostic First Steps

Run these two commands before anything else. They give you the most useful diagnostic information and confirm whether the camera is visible to the OS at all.

```bash
# Ask rpicam to list all detected cameras
rpicam-hello --list-cameras
```

```bash
# Check the kernel log for camera-related messages
dmesg | grep -i camera
```

If `rpicam-hello --list-cameras` returns `No cameras available`, your problem is below the Python layer — start with the hardware checks. If it shows your camera model (e.g., `imx708`), the hardware is fine and your problem is in the Python/library layer.

---

## Problem: "No cameras available" or Camera Not Detected

This is the most common first-time issue and it's almost always physical or OS-level.

**Check the ribbon cable first.** Unplug the Pi's power completely before touching anything. Remove the ribbon cable, inspect it for bends, creases, or torn edges near the connector, and reseat it firmly. The exposed metal contacts must face toward the connector body, not away from it. The latch must click closed with even pressure on both sides. A cable inserted at a slight angle is probably the most common cause of this error.

**Try a different cable if you have one.** Ribbon cables can develop hairline fractures from repeated flexing that are invisible to the eye.

**Confirm the camera interface is enabled:**

```bash
sudo raspi-config
# Navigate to Interface Options → Camera → Enable
sudo reboot
```

On Raspberry Pi OS Bookworm, the camera is normally enabled by default, but it's worth confirming.

**Check that `/dev/video0` (or similar) exists.** After rebooting, run `ls /dev/video*`. On a working system with a camera connected, you should see at least one device listed. No output suggests the camera driver didn't load.

**Confirm GPU memory is sufficient.** This matters more on older Pi models. Run `sudo raspi-config`, go to Advanced Options → Memory Split, and make sure the value is at least 128.

---

## Problem: libcamera-hello: "command not found" (or any libcamera-* command)

The camera tools were renamed from `libcamera-*` to `rpicam-*` in recent versions of Raspberry Pi OS. If you followed an older tutorial that references `libcamera-hello`, `libcamera-still`, or `libcamera-vid`, simply substitute `rpicam-` in place of `libcamera-` and the commands will work. The old package name `libcamera-apps` still installs correctly — it now acts as a pointer to `rpicam-apps` — so the installation step in older guides isn't broken, just the command names at the end of it.

---

## Problem: `ImportError: No module named 'picamera2'`

Python can't find the library. The most common cause is using a different Python environment than the one where the library is installed. On Raspberry Pi OS, Picamera2 is installed at the system level.

```bash
# Check whether it's installed
pip3 show picamera2

# If not found, install it
sudo apt install python3-picamera2
```

If you're using a virtual environment, be aware that virtual environments on Raspberry Pi don't inherit system packages by default. The simplest solution is to use the system Python for camera work, or create your virtual environment with `--system-site-packages`:

```bash
python3 -m venv --system-site-packages my_camera_env
```

---

## Problem: `Camera in use by another application`

libcamera enforces exclusive access — only one application can hold the camera open at a time. Something else already has it.

```bash
# Find what's using the camera device
sudo lsof /dev/video0

# Or look for any running camera-related Python scripts
ps aux | grep -E "picamera|libcamera|python"
```

If you see a previous version of your own script, it means a prior run crashed without calling `picam2.stop()`. Kill it by PID:

```bash
kill <PID>
```

To prevent your own scripts from leaving the camera held open after a crash, wrap your camera code in a `try/finally` block:

```python
picam2 = Picamera2()
picam2.start()
try:
    # Your camera code here
    picam2.capture_file("test.jpg")
finally:
    # This runs even if an exception occurs
    picam2.stop()
```

---

## Problem: Image Is Completely Black

A completely black image — not just dark, genuinely zero brightness — points to specific issues.

First, confirm the lens cap is removed if you have an HQ Camera with a C/CS-mount lens.

Second, check the ribbon cable is making good contact. A partially connected cable can allow the camera to be detected but produce no image data.

Third, try explicitly using a still configuration with a longer warm-up:

```python
config = picam2.create_still_configuration()
picam2.configure(config)
picam2.start()
time.sleep(3)    # Give auto-exposure more time than usual
picam2.capture_file("test.jpg")
```

Fourth, check the exposure metadata to see what settings the camera chose:

```python
metadata = picam2.capture_metadata()
print(f"Exposure time: {metadata.get('ExposureTime')} µs")
print(f"Analogue gain: {metadata.get('AnalogueGain')}")
```

If the exposure time is very low (like 100µs or less) in a dimly lit room, the camera may be struggling with extreme darkness. Try pointing it at a brighter subject for testing.

---

## Problem: Image Is Overexposed (Too Bright / Washed Out)

Usually caused by capturing before auto-exposure has stabilized. The two-second warm-up sleep is there for exactly this reason. If you're still getting overexposed images, increase the sleep to 3 or 4 seconds, especially in challenging lighting conditions.

If the overexposure is persistent even after a long warm-up:

```python
picam2.set_controls({
    "AeEnable": True,          # Enable auto-exposure
    "AeMeteringMode": 0,       # 0 = centre-weighted metering
    "Brightness": 0.0          # Make sure brightness isn't artificially boosted
})
time.sleep(2)
picam2.capture_file("test.jpg")
```

---

## Problem: Preview Window Does Not Appear

If you're running the Pi **headlessly** (no monitor, accessed via SSH), a Qt preview window has nowhere to display. Use `NullPreview` for headless operation, or stream the preview over the network or save frames to disk for inspection.

If you're on a **desktop** but the window doesn't appear, make sure your DISPLAY variable is set:

```bash
echo $DISPLAY    # Should print :0 or :0.0 on a local desktop session
```

In SSH sessions, you need X11 forwarding enabled (`ssh -X`) or a VNC connection. If running in a terminal on the desktop itself and the window still doesn't appear, try `DrmPreview`:

```python
from picamera2.previews import DrmPreview
picam2.start_preview(DrmPreview())
```

---

## Problem: Poor Image Quality (Noise, Blur, Color Cast)

**Grainy / noisy image**: The camera is in a low-light situation and the auto-exposure algorithm has increased the analogue gain to compensate. High gain amplifies both signal and noise. Solutions include increasing ambient light, or enabling stronger noise reduction:

```python
picam2.set_controls({"NoiseReductionMode": 2})  # 2 = High quality noise reduction
```

**Motion blur**: The exposure time is too long for the subject's movement. Set a shorter exposure time manually and increase gain to compensate:

```python
# Fast shutter for freezing motion
picam2.set_controls({
    "ExposureTime": 5000,    # 5ms
    "AnalogueGain": 4.0      # Increase gain to compensate for the lost light
})
```

**Colour cast**: Auto white balance may be struggling. Lock it to a specific mode that matches your lighting:

```python
# 0=Auto, 1=Tungsten, 2=Fluorescent, 3=Indoor, 4=Daylight, 5=Cloudy
picam2.set_controls({"AwbMode": 4})   # Daylight, for outdoor shooting
```

---

## Problem: `capture_array()` Shape Is Unexpected

The default array format includes an alpha channel (XBGR8888 or XRGB8888), giving you 4 channels per pixel rather than 3. This surprises many people coming from OpenCV or PIL tutorials that assume 3-channel RGB arrays.

```python
image = picam2.capture_array()
print(image.shape)    # Might be (height, width, 4)

# Strip the alpha channel to get plain RGB
rgb = image[:, :, :3]

# Or configure the camera to output RGB888 directly
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"}
)
```

If you're passing the array to OpenCV, note that OpenCV expects BGR channel order, not RGB:

```python
import cv2
image = picam2.capture_array()
bgr = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2BGR)
```

---

## Useful Diagnostic Commands

```bash
# Full camera system information
rpicam-hello --list-cameras

# Check the kernel log for hardware errors
dmesg | grep -iE "camera|imx|ov5647|imx477|imx708"

# Check Picamera2 version
python3 -c "import picamera2; print(picamera2.__version__)"

# Print all available controls and their valid ranges
python3 -c "
from picamera2 import Picamera2
p = Picamera2()
for name, ctrl in p.camera_controls.items():
    print(f'{name}: {ctrl}')
p.close()
"

# Check that all dependencies are present
python3 -c "import numpy; import PIL; import libcamera; print('All dependencies OK')"

# Check if gpiozero is installed (for button project)
python3 -c "import gpiozero; print('gpiozero OK')"

# List currently running Python scripts using the camera
ps aux | grep python3
```

---

## Still Stuck?

The [Raspberry Pi Forums — Camera section](https://forums.raspberrypi.com/viewforum.php?f=43) is the most active place for Pi Camera discussion and is monitored by Raspberry Pi engineers.

The [Picamera2 GitHub Issues page](https://github.com/raspberrypi/picamera2/issues) is the right place to report bugs or search for known issues that match your symptoms.

When asking for help, include the output of `rpicam-hello --list-cameras`, your OS version (`cat /etc/os-release`), your Python version (`python3 --version`), and the full error traceback from your script.