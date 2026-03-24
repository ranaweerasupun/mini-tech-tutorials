# Writing Your First Linux Kernel Driver: I2C Temperature Sensor

A step-by-step tutorial for C programmers who want to understand how Linux
kernel drivers actually work — built around a single, real goal: writing a
driver for the TMP102 I2C temperature sensor on a Raspberry Pi that exposes
live temperature readings through the Linux hardware monitoring subsystem.

---

## What This Tutorial Builds Toward

By the end, you will have written a kernel module in C that:

- Speaks the I2C protocol to a real hardware sensor
- Integrates with the Linux device model using the probe/remove pattern
- Exposes temperature readings as a virtual file under `/sys/class/hwmon/`
- Works correctly with standard tools like `sensors` and `lm-sensors`

Running `cat /sys/class/hwmon/hwmon1/temp1_input` and seeing your room
temperature come back from code you wrote — code running inside the kernel
itself — is the moment this tutorial is aimed at.

---

## Who This Is For

This tutorial is written for people who know C basics — structs, pointers,
functions, header files — but have never written kernel code before. No prior
experience with Linux internals, device drivers, or embedded systems is assumed.
Every concept that needs to exist before another concept can make sense is
introduced before it is needed.

---

## Tutorial Structure

Each document builds directly on the ones before it. Read them in order.

| # | Document | What it covers |
|---|----------|---------------|
| 01 | [The Linux Kernel and Kernel Modules](docs/01-kernel-and-modules.md) | What the kernel is, user space vs kernel space, what a module is |
| 02 | [Your First Kernel Module](docs/02-hello-module.md) | Building, loading, and unloading a minimal "hello world" module |
| 03 | [The Linux Device Model](docs/03-device-model.md) | Drivers, devices, buses, the probe pattern, and `devm_` memory management |
| 04 | [Device Trees](docs/04-device-trees.md) | What device trees are, overlays, and the compatible string link to drivers |
| 05 | [I2C Protocol and the Kernel I2C Subsystem](docs/05-i2c.md) | I2C fundamentals, the kernel I2C API, SMBus, and `i2cdetect` |
| 06 | [The hwmon Subsystem](docs/06-hwmon.md) | What hwmon is, sysfs attributes, and how `lm-sensors` reads your data |
| 07 | [Building the TMP102 Driver](docs/07-tmp102-driver.md) | The complete driver explained line by line |
| 08 | [Troubleshooting](docs/08-troubleshooting.md) | Common errors decoded with step-by-step fixes |

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

Standalone, buildable code lives in the `examples/` directory. Each one
corresponds to a stage in the tutorial and can be built and loaded independently.

- [`examples/01_hello_module/`](examples/01_hello_module/) — A minimal kernel module: just init and exit
- [`examples/02_i2c_detect_module/`](examples/02_i2c_detect_module/) — A module that detects and probes an I2C device
- [`examples/03_tmp102_driver/`](examples/03_tmp102_driver/) — The complete TMP102 driver with device tree overlay

---

## Requirements

- Raspberry Pi running Raspberry Pi OS Bookworm (64-bit recommended)
- Kernel headers installed: `sudo apt install raspberrypi-kernel-headers`
- I2C tools: `sudo apt install i2c-tools`
- Device tree compiler: `sudo apt install device-tree-compiler`
- GCC and build tools: `sudo apt install build-essential`

---

## License

Released under the [MIT License](LICENSE). The kernel module source files
are additionally licensed under GPL-2.0, which is required for kernel modules.
