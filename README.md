# Short Tutorials

A growing collection of short, focused tutorials on topics across electronics, embedded systems, Linux, IoT, edge computing, web development, robotics, and nanotechnology.

The goal is simple: pick one specific thing, explain it well, and stop. No fluff, no filler, no five-page intro before you write a single line of code. Each tutorial is self-contained and can be finished in a sitting.

---

## What's Here Now

### Raspberry Pi & Linux

| Tutorial | What it covers |
|----------|----------------|
| [GStreamer on Raspberry Pi 5](gstreamer-tutorial/) | Building hardware-accelerated video pipelines in Python — from zero GStreamer knowledge to H.264 encoding using the Pi 5's hardware encoder |
| [Writing a Linux Kernel Driver](i2c-driver-tutorial/) | A real I2C driver for the TMP102 temperature sensor, from blank `.c` file to live readings through the hwmon subsystem |
| [Raspberry Pi Camera with Python](raspberry-pi-camera-tutorial/) | Picamera2 from first photo through motion detection, time-lapses, and numpy frame processing |
| [Running Apps as systemd Services](systemd-services-tutorial/) | Service files, restart policies, logging, environment variables, and timers — the gap between "works when I run it" and "runs forever on its own" |

More topics are on the way. The table above will grow.

---

## What's Coming

These are still being written — listed here so you know what's in the queue:

**Electronics & Embedded**
- Reading datasheets without losing your mind
- I2C and SPI from first principles — what's actually happening on the wire
- Choosing a microcontroller for a project (and why the answer isn't always Arduino)
- PCB design basics — from schematic to manufactured board

**Linux & Systems**
- Device tree overlays — writing and compiling your own
- V4L2 and the Linux camera stack below Picamera2
- GPIO and interrupts in C — kernel-side, not Python
- Cross-compiling for ARM on a desktop machine

**IoT & Edge Computing**
- MQTT from scratch — brokers, clients, QoS levels, and what happens when the network drops
- Persistent offline queuing for unreliable edge networks
- Running inference on-device — picking the right model size for constrained hardware

**Web Development**
- WebSockets for real-time sensor dashboards
- Building a minimal REST API for hardware control
- Serving data from an embedded device over a local network

**Robotics**
- ROS2 basics — nodes, topics, and why it works the way it does
- Motor control fundamentals — PWM, H-bridges, and feedback
- Sensor fusion: combining IMU, GPS, and encoders

**Nanotechnology**
- Nanomaterials in electronics — what engineers actually need to know
- MEMS sensors — how accelerometers and gyroscopes work at the device level

No fixed schedule. Topics get added when they're ready and properly explained, not before.

---

## How These Are Written

Every tutorial picks one concrete goal — something real, not a contrived example — and builds toward it. The concepts you need are introduced before you need them. By the time you're writing code or wiring something up, the reasoning behind it should already be clear.

They're short by design. The aim is that you can finish one in a couple of hours, come away with something working, and actually understand what you built.

---

## Who This Is For

If you're comfortable with the basics and want to go a level deeper — whether that's your first kernel module, your first video pipeline, or your first PCB — these are written with you in mind.

Some tutorials assume programming experience, some assume electronics background, some assume neither. Each one says upfront what you need to know to follow along.

---

## Structure

Every tutorial follows the same layout:

```
tutorial-name/
├── README.md       # Overview, what you need, quick start
├── docs/           # The tutorial itself, split into short numbered sections
└── examples/       # Complete, runnable code for each stage
```

The docs read in order. The examples run independently.

---

## License

Everything here is released under the [MIT License](LICENSE), except kernel module source files which are GPL-2.0 as required by the Linux kernel.

Use these however you like.