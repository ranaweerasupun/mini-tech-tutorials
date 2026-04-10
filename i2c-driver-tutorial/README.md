# Writing Your First Linux Kernel Driver: I2C Temperature Sensor

[![License: GPL-2.0](https://img.shields.io/badge/Kernel%20Modules-GPL--2.0-red.svg)](LICENSE)
[![License: MIT](https://img.shields.io/badge/Other%20Code-MIT-blue.svg)](LICENSE)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/Content-CC--BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

A step-by-step tutorial for C programmers who want to understand how Linux kernel drivers actually work — built around a real goal: writing a driver for the TMP102 I2C temperature sensor on a Raspberry Pi that surfaces live temperature readings through the Linux hardware monitoring subsystem.

---

## What This Tutorial Builds Toward

By the end, you'll have written a kernel module in C that:

- Speaks the I2C protocol to a real hardware sensor
- Integrates with the Linux device model using the probe/remove pattern
- Exposes temperature readings as a virtual file under `/sys/class/hwmon/`
- Works out of the box with standard tools like `sensors` and `lm-sensors`

Running `cat /sys/class/hwmon/hwmon1/temp1_input` and seeing your room temperature come back from code you wrote — code running inside the kernel itself — is the moment this tutorial is aimed at. It's a good one.

---

## Who This Is For

This is written for people who know C — structs, pointers, functions, header files — but have never written kernel code before. No prior experience with Linux internals, device drivers, or embedded systems is assumed. Every concept that needs to exist before another one can make sense gets introduced before it's needed.

If you've ever tried to figure this out from the official kernel documentation or random blog posts, you know how scattered it can be. The docs assume you already know what they're supposed to be teaching, the AI-generated answers look plausible until you try them, and the working examples you do find are usually too complex to learn from. This tutorial tries to actually fill that gap.

---

## Tutorial Structure

Each document builds directly on the ones before it. Read them in order.

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [The Linux Kernel and Kernel Modules](docs/01-kernel-and-modules.md) | What the kernel actually is, user space vs kernel space, what a module is and how it differs from a regular program |
| 02 | [Your First Kernel Module](docs/02-hello-module.md) | Building, loading, and unloading a minimal hello-world module — making the toolchain feel real before adding complexity |
| 03 | [The Linux Device Model](docs/03-device-model.md) | Drivers, devices, buses, the probe pattern, private data structs, `devm_` memory management, and mutexes |
| 04 | [Device Trees](docs/04-device-trees.md) | What device trees are, how overlays work, the compatible string link between hardware and driver |
| 05 | [I2C Protocol and the Kernel I2C Subsystem](docs/05-i2c.md) | I2C fundamentals, registers, SMBus, the i2c_client struct, and testing with i2c-tools |
| 06 | [The hwmon Subsystem](docs/06-hwmon.md) | sysfs, kernel attributes, SENSOR_DEVICE_ATTR, attribute groups, and how lm-sensors reads your data |
| 07 | [Building the TMP102 Driver](docs/07-tmp102-driver.md) | The complete driver, line by line, with every pattern tied back to where you learned it |
| 08 | [Troubleshooting](docs/08-troubleshooting.md) | A layered diagnostic guide — hardware, device tree, build, and driver — for when things don't work |

---

## Hardware Required

- Raspberry Pi with a 40-pin GPIO header (Pi 4 recommended)
- TMP102 temperature sensor breakout board
- Four jumper wires

Wiring:

```
TMP102 Pin   →   Raspberry Pi Pin
──────────────────────────────────
VCC          →   Pin 1  (3.3V)
GND          →   Pin 6  (GND)
SDA          →   Pin 3  (GPIO 2 / I2C SDA)
SCL          →   Pin 5  (GPIO 3 / I2C SCL)
ADD0         →   Pin 6  (GND — sets I2C address to 0x48)
```

---

## Examples

Each example in `examples/` corresponds to a stage in the tutorial and can be built and loaded independently.

- [`examples/01_hello_module/`](examples/01_hello_module/) — A minimal module: just init and exit. Gets the build toolchain working before anything else.
- [`examples/02_i2c_detect_module/`](examples/02_i2c_detect_module/) — A module that finds and probes the TMP102 over I2C, without yet exposing any data to user space.
- [`examples/03_tmp102_driver/`](examples/03_tmp102_driver/) — The complete driver with device tree overlay. The finished product.

---

## Requirements

- Raspberry Pi running Raspberry Pi OS Bookworm (64-bit recommended)
- Kernel headers: `sudo apt install raspberrypi-kernel-headers`
- I2C tools: `sudo apt install i2c-tools`
- Device tree compiler: `sudo apt install device-tree-compiler`
- GCC and build tools: `sudo apt install build-essential`

---

## Contributing

Contributions are welcome. If you spot an error, want to add a project, or have a better explanation for something, open an issue or submit a pull request.

---

## License

**Kernel module source files** (all `.c` files and `Makefile`) — [GPL-2.0](LICENSE), as required for Linux kernel modules
**Device tree files** (all `.dts` files) — [MIT License](LICENSE)
**Tutorial content** (all `.md` files and written documentation) — [CC BY-NC 4.0](LICENSE)

The kernel module code must be GPL-2.0 — this is a hard requirement of the Linux kernel, not a choice. The device tree overlays and any other non-kernel code are MIT licensed and free to use in your own projects without restriction. The written tutorials may be shared and adapted for non-commercial purposes with attribution, but may not be repackaged or sold.

© 2025 Supun Akalanka Sriyananda