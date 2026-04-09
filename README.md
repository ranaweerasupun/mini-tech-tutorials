# Raspberry Pi Tutorials

A collection of hands-on tutorials for people who want to go a level deeper with their Raspberry Pi — past running scripts someone else wrote, into actually understanding the system underneath.

These started as notes I kept while figuring things out myself. The official documentation is often accurate but rarely explains *why* things work the way they do, which makes it hard to adapt when something goes wrong or when you want to do something slightly different. These tutorials try to fill that gap.

Each one is built around a real, working goal — not a toy example, but something you'd actually want to build. The explanations cover the concepts you need before you need them, so by the time you're writing code or config, the pieces should already make sense.

---

## Tutorials

### [GStreamer on Raspberry Pi 5](gstreamer-tutorial/)
**Build a hardware-accelerated video pipeline in Python**

GStreamer has a steep initial learning curve — the mental model is unfamiliar and the error messages aren't particularly helpful until you know what to look for. This tutorial builds that mental model first, then puts it to use capturing 720p video from a USB webcam and encoding it to H.264 using the Pi 5's hardware encoder. The difference between software encoding (~80% CPU) and hardware encoding (~15% CPU) is dramatic and immediately tangible.

No prior GStreamer experience needed. Basic Python is enough to start.

→ [Go to tutorial](gstreamer-tutorial/README.md)

---

### [Writing a Linux Kernel Driver](i2c-driver-tutorial/)
**A real I2C driver for the TMP102 temperature sensor**

Kernel development has a reputation for being inaccessible, and most tutorials either go too shallow ("here's a hello world module, good luck") or assume you already understand the device model, the bus subsystem, and memory management patterns. This one doesn't. It takes you from a blank `.c` file to a driver that reads live temperature data from real hardware and surfaces it through the standard Linux hwmon interface — the same one `sensors` and `lm-sensors` use.

You'll need C basics — structs, pointers, header files — but no kernel experience.

→ [Go to tutorial](i2c-driver-tutorial/README.md)

---

### [Raspberry Pi Camera with Python](raspberry-pi-camera-tutorial/)
**From first photo to motion detection, time-lapses, and numpy arrays**

Picamera2 is the current library for the Pi camera and it's genuinely good, but the documentation is dense and the architecture takes some getting used to. This tutorial covers the basics, the architecture, and then a set of practical projects: time-lapses, button-triggered captures, frame-differencing motion detection, and H.264 video recording. The motion detection section in particular gets into some interesting territory with numpy arrays and frame comparison.

Works with any Pi Camera module (v1, v2, v3, HQ) on Pi 3, 4, 5, or Zero 2 W.

→ [Go to tutorial](raspberry-pi-camera-tutorial/README.md)

---

### [Running Applications as systemd Services](systemd-services-tutorial/)
**Stop babysitting your Pi — let systemd do it**

There's a gap between "script that works when I run it" and "thing that starts on boot, restarts when it crashes, and logs properly." systemd fills that gap, and once you've written a few service files it becomes second nature. This tutorial covers service files from scratch, restart policies, dependency ordering, environment files for secrets and config, logging with journalctl, and systemd timers as a cleaner alternative to cron.

Works on any modern Linux system, not just Raspberry Pi.

→ [Go to tutorial](systemd-services-tutorial/README.md)

---

## Who These Are For

These tutorials are written for people who are comfortable with the basics and want to go further — hobbyists who've outgrown copy-pasting scripts, engineering students wanting hands-on Linux and embedded experience, and developers from other backgrounds who are new to this kind of systems-level work.

They're not written for complete beginners and they're not written for kernel engineers who've been doing this for twenty years. The target is somewhere in the middle: technically comfortable, but new to this specific territory.

---

## What's Coming

More tutorials are planned. Topics in the queue include:

- **MQTT on the Pi** — connecting sensors to a broker, handling unreliable networks, persistent message queuing
- **Device Tree Overlays** — writing and compiling your own overlays from scratch
- **V4L2 and camera pipelines** — going below Picamera2 to understand the capture stack
- **GPIO and interrupts in C** — kernel-side GPIO handling, not just the Python libraries

No fixed schedule. They come out when they're ready and properly explained.

---

## Structure

Every tutorial follows the same pattern:

```
tutorial-name/
├── README.md          # Overview, prerequisites, quick start
├── docs/              # The actual tutorial, split into numbered documents
│   ├── 01-...md
│   ├── 02-...md
│   └── ...
└── examples/          # Standalone, runnable code for each stage
```

The docs are meant to be read in order. The examples can be run independently — each one is a complete, working program, not a fragment.

---

## License

All tutorials and code examples are released under the [MIT License](LICENSE), except for kernel module source files which carry the GPL-2.0 license as required for Linux kernel code.

Use these however you like. If something here helped you, pass it on.
