"""
button_trigger.py
-----------------
Captures a photo whenever a physical push button is pressed.
Uses GPIO 17 (Pin 11) with a pull-up resistor configuration.

Wiring:
  Button leg 1  → 3.3V (Pin 1)
  Button leg 2  → GPIO 17 (Pin 11)
  10kΩ resistor → between GPIO 17 and GND (Pin 6)

With this wiring the pin reads LOW normally and HIGH when pressed.
The gpiozero library handles the edge detection in a background thread,
so the main thread just waits quietly with signal.pause().

Dependencies:
  pip install gpiozero   (usually pre-installed on Raspberry Pi OS)

Run: python3 button_trigger.py
"""

from picamera2 import Picamera2
from gpiozero import Button
import time
import signal
import sys

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
BUTTON_GPIO_PIN = 17     # BCM GPIO number (not the physical pin number)
# -----------------------------------------------------------------------

picam2 = Picamera2()
picam2.start()

print("Warming up auto-exposure...")
time.sleep(2)

# pull_up=False because our wiring uses an external pull-down resistor.
# gpiozero supports both pull_up=True (internal pull-up, active LOW)
# and pull_up=False (external pull-down or active HIGH).
button = Button(BUTTON_GPIO_PIN, pull_up=False)

photo_count = 0


def take_photo():
    """Called automatically by gpiozero whenever the button is pressed."""
    global photo_count
    photo_count += 1
    filename = f"capture_{photo_count:04d}.jpg"

    picam2.capture_file(filename)
    print(f"  📷 Saved {filename}")


# Register the callback. gpiozero monitors the GPIO pin in a background
# thread and calls this function on every press event.
button.when_pressed = take_photo

print(f"Camera ready on GPIO {BUTTON_GPIO_PIN}.")
print("Press the button to capture. Press Ctrl+C to quit.\n")

try:
    # signal.pause() suspends the main thread efficiently without burning
    # CPU in a polling loop. The background thread continues watching the pin.
    signal.pause()

except KeyboardInterrupt:
    picam2.stop()
    print(f"\nDone. {photo_count} photo(s) captured.")
    sys.exit(0)
