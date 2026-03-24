# 08 — Troubleshooting

Kernel driver development involves more places for things to go wrong than most programming because failures can occur at the hardware layer, the kernel configuration layer, the device tree layer, the module build layer, or the driver code itself. This guide helps you isolate which layer the problem is in and what to do about it — because once you know where the problem lives, the fix is almost always straightforward.

The general principle is to start at the bottom and work upward. There is no point debugging your driver code if the hardware is not connected correctly, and there is no point debugging the device tree if the kernel cannot even see the I2C bus.

---

## Layer 1: Hardware and I2C Connectivity

**Run this first, before anything else:**

```bash
sudo i2cdetect -y 1
```

What the output tells you:

A `48` in the grid means the TMP102 is physically present and responding to I2C address scans. This is the only outcome that means the hardware layer is working. Everything else in this tutorial depends on this check passing.

A `UU` at position 48 means the kernel already has a driver bound to that device — possibly the built-in TMP102 driver that ships with the mainline kernel. Unload it first: `sudo rmmod tmp102` (the mainline driver), then try again. If `UU` persists, a different driver has claimed the device.

Dashes `--` everywhere, including at position 48, mean the sensor is not responding. In this case, work through this physical checklist before touching any software: confirm VCC is connected to 3.3V (not 5V), confirm GND is connected to a ground pin, confirm SDA goes to Pin 3 (GPIO2) and SCL goes to Pin 5 (GPIO3), confirm ADD0 is connected to GND (not floating), and confirm the ribbon cable or jumper wires are making solid contact. It is also worth trying `i2cdetect -y 0` — on some early Pi models the external I2C bus is bus 0, not bus 1.

---

## Layer 2: I2C Bus Enabled in the OS

If `i2cdetect -y 1` gives you an error like "Error: Could not open file /dev/i2c-1", the I2C interface is not enabled in the OS:

```bash
sudo raspi-config
# Interface Options → I2C → Yes
# Exit and reboot
```

After rebooting, also confirm the kernel module for the I2C bus is loaded:

```bash
lsmod | grep i2c_bcm2835
```

If it does not appear, load it manually: `sudo modprobe i2c-bcm2835`. If the module does not exist, the kernel image may not include I2C support — this should not happen on a standard Raspberry Pi OS image.

---

## Layer 3: Device Tree Overlay

After the hardware and OS layers are verified, check whether the device tree overlay was applied correctly.

First, confirm the compiled overlay file is in the right place:

```bash
ls /boot/overlays/tmp102-overlay.dtbo
```

If the file is missing, the dtc compilation or the copy step was skipped. Re-run:

```bash
dtc -@ -I dts -O dtb -o tmp102-overlay.dtbo tmp102-overlay.dts
sudo cp tmp102-overlay.dtbo /boot/overlays/
```

Second, confirm the overlay is referenced in the boot configuration:

```bash
grep "tmp102-overlay" /boot/firmware/config.txt
```

On older Raspberry Pi OS images, the config file may be at `/boot/config.txt` rather than `/boot/firmware/config.txt`. Check both if the first gives no result. If the line is missing, add it and reboot:

```bash
echo "dtoverlay=tmp102-overlay" | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

Third, after rebooting, confirm the kernel processed the overlay and registered the device:

```bash
ls /sys/bus/i2c/devices/
```

You should see a `1-0048` entry. Its presence means the device tree node was found and the kernel has created a device record for the sensor. If `1-0048` is absent, the overlay was not applied — double-check the filename in `/boot/firmware/config.txt` matches the `.dtbo` file exactly (without the `.dtbo` extension).

If `1-0048` is present, verify the compatible string was read correctly:

```bash
cat /sys/bus/i2c/devices/1-0048/of_node/compatible
```

This must print `ti,tmp102`. If it prints something different, the DTS file has a typo in the compatible string — it will never match your driver's `of_device_id` table.

---

## Layer 4: Module Build

If the hardware and device tree layers are working, check that the module built successfully.

The most common build failure is a kernel header version mismatch:

```bash
# The kernel the module was built against
modinfo tmp102.ko | grep vermagic

# The kernel currently running
uname -r
```

These must match exactly. If they differ, the kernel headers installed do not correspond to the running kernel. This can happen after a kernel update where the headers were not updated simultaneously. Fix it:

```bash
sudo apt update && sudo apt install raspberrypi-kernel-headers
# Then rebuild the module:
make clean && make
```

A second common build issue is a missing or incorrect Makefile. If `make` gives "No rule to make target" or "missing separator", the Makefile has a problem. The indented lines must use tab characters — spaces will produce the "missing separator" error. Open the Makefile in a hex editor or run `cat -A Makefile` and verify the indented lines begin with `^I` (the tab indicator) rather than spaces.

---

## Layer 5: Driver Loading and Probe

After the module builds successfully, loading it and checking the kernel log tells you whether `probe` was called and whether it succeeded:

```bash
sudo insmod tmp102.ko
dmesg | tail -10
```

**If you see "TMP102 found! Initial temperature: XX.XXX°C"**, the driver loaded successfully. Skip to the reading verification below.

**If you see "Could not read from TMP102 — check your wiring"**, the `probe` function was called (the device tree match worked) but the I2C read failed. The sensor is registered in the device tree but not physically responding. Go back to layer 1 and re-verify the hardware.

**If you see nothing at all from `tmp102`**, the `probe` function was never called. This means the device tree match failed — the compatible string in the overlay does not match the `of_device_id` table in the driver. Compare them character by character: the DTS must say `compatible = "ti,tmp102"` and the driver must have `.compatible = "ti,tmp102"` in its `of_match_table`. Even a single character difference (an underscore instead of a hyphen, wrong capitalisation) prevents the match.

**If `insmod` gives "Operation not permitted" or "Invalid module format"**, either you need `sudo` in front of `insmod`, or the module's vermagic does not match the running kernel (addressed in layer 4 above).

---

## Layer 6: Reading the Temperature

If the driver loaded successfully but reading the sysfs file produces unexpected results:

```bash
cat /sys/class/hwmon/hwmon*/name
```

This shows the name of every hwmon device registered on the system. Find the one that says `tmp102`. Note its number (e.g., `hwmon2`), then read from that specific device:

```bash
cat /sys/class/hwmon/hwmon2/temp1_input
```

If this produces a reasonable number (room temperature is typically 18000 to 28000 — i.e. 18–28°C in millidegrees), the driver is working correctly.

If the value seems wrong — consistently too high or too low — check the arithmetic in `tmp102_read_temperature`. You can verify against a raw register read:

```bash
# Read the raw register value
sudo i2cget -y 1 0x48 0x00 w
```

Take the raw value (e.g., `0xd817`), swap the bytes (to `0x17d8`), shift right by 4 (to `0x17d` = 381 decimal), multiply by 1000 and divide by 16 (381 × 1000 / 16 = 23812), and you should get approximately what `temp1_input` reports. If the driver's value and the manual calculation agree, the driver is correct and the temperature reading is valid.

---

## Diagnostic Command Reference

This collects the most useful diagnostic commands in one place for quick access when something is not working.

```bash
# Hardware: is the sensor visible on the I2C bus?
sudo i2cdetect -y 1

# Hardware: read a register directly (bypasses any driver)
sudo i2cget -y 1 0x48 0x00 w

# OS: is the I2C bus driver loaded?
lsmod | grep i2c

# Device tree: did the overlay create a device entry?
ls /sys/bus/i2c/devices/

# Device tree: what compatible string did the kernel read?
cat /sys/bus/i2c/devices/1-0048/of_node/compatible

# Module: does the built module match the running kernel?
modinfo tmp102.ko | grep vermagic
uname -r

# Module: is it currently loaded?
lsmod | grep tmp102

# Driver: what did probe log?
dmesg | grep tmp102

# Driver: what is the full recent kernel log?
dmesg | tail -30

# Reading: what hwmon devices are registered?
cat /sys/class/hwmon/hwmon*/name

# Reading: what is the temperature?
cat /sys/class/hwmon/hwmon*/temp1_input
```

One final note on general kernel debugging practice: `dmesg -w` (or `dmesg --follow`) is the kernel equivalent of `tail -f` — it shows new kernel log messages as they arrive in real time. Running it in a second terminal while you load your module in the first gives you immediate visibility into what the kernel thinks is happening, without having to repeatedly run `dmesg | tail` after each action.
