# Short Tutorials

A growing collection of short, focused tutorials across electronics, embedded systems, Linux, IoT, edge computing, web development, robotics, and nanotechnology.

---

## Why This Exists

You know that specific kind of frustration where you're trying to do something that *should* be straightforward, but the official docs assume you already know half the things they're supposed to be teaching you? And the Stack Overflow answers are five years old and reference an API that no longer exists? And you ask an AI and it confidently generates something that looks plausible, compiles (maybe), and then just doesn't work — and when you ask why, it apologises and generates a slightly different version that also doesn't work?

Yeah. That's what this is for.

These tutorials come out of real hours spent getting things wrong, reading source code because the docs didn't cover it, and eventually landing on something that actually works. The goal is to write that down properly — not just the *what*, but the *why* — so you don't have to repeat the same detours.

Each one is short and covers one thing. You should be able to finish it in a sitting and walk away with something working and actually understood.

---

## What's Here Now

### Raspberry Pi & Linux

| Tutorial | What it covers |
|----------|----------------|
| [GStreamer on Raspberry Pi 5](gstreamer-tutorial/) | Building hardware-accelerated video pipelines in Python — from zero GStreamer knowledge to H.264 encoding using the Pi 5's hardware encoder |
| [Writing a Linux Kernel Driver](i2c-driver-tutorial/) | A real I2C driver for the TMP102 temperature sensor, from blank `.c` file to live temperature readings through the hwmon subsystem |
| [Raspberry Pi Camera with Python](raspberry-pi-camera-tutorial/) | Picamera2 from first photo through motion detection, time-lapses, and numpy frame processing |
| [Running Apps as systemd Services](systemd-services-tutorial/) | Service files, restart policies, logging, environment variables, and timers — bridging the gap between "works when I run it" and "runs forever on its own" |

More topics coming. The table above will grow.

---

## What's Coming

Still being written, but here's what's in the queue:

**Electronics & Embedded**
- Reading datasheets without losing your mind
- I2C and SPI from first principles — what's actually on the wire
- Choosing a microcontroller for a project (and why the answer isn't always Arduino)
- PCB design basics — from schematic to manufactured board

**Linux & Systems**
- Device tree overlays — writing and compiling your own
- V4L2 and the Linux camera stack, below Picamera2
- GPIO and interrupts in C — kernel-side, not the Python libraries
- Cross-compiling for ARM on a desktop machine

**IoT & Edge Computing**
- MQTT from scratch — brokers, clients, QoS, and what happens when the network drops
- Persistent offline queuing for unreliable edge networks
- Running inference on-device — picking the right model size for constrained hardware

**Web Development**
- WebSockets for real-time sensor dashboards
- A minimal REST API for hardware control
- Serving data from an embedded device over a local network

**Robotics**
- ROS2 basics — nodes, topics, and why it works the way it does
- Motor control fundamentals — PWM, H-bridges, and feedback loops
- Sensor fusion: combining IMU, GPS, and encoders

**Nanotechnology**
- Nanomaterials in electronics — what engineers actually need to know
- MEMS sensors — how accelerometers and gyroscopes work at the device level

No fixed schedule. Things get published when they're properly explained, not before.

---

## Who This Is For

Fellow engineers, developers, hobbyists, students — anyone who's comfortable enough with the basics but keeps hitting walls when trying to go deeper. If you've ever spent three hours on something that turned out to have a two-line fix that nobody wrote down anywhere, this is written for you.

Some tutorials lean more hardware, some more software. Each one says upfront what background is helpful, so you're not halfway through before realising you're missing something.

---

## Structure

Every tutorial follows the same layout:

```
tutorial-name/
├── README.md       # Overview, prerequisites, quick start
├── docs/           # The tutorial, split into short numbered sections
└── examples/       # Complete, runnable code for each stage
```

Docs are meant to be read in order. Examples can be run independently — each one is a complete working program, not a fragment you have to assemble.

---

## License

Everything here is MIT licensed, except kernel module source files which carry GPL-2.0 as required for Linux kernel code.

Use these however you like. If something here saved you a few hours, hopefully it pays forward somewhere.