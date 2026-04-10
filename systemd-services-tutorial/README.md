# systemd Services Tutorial

[![License: MIT](https://img.shields.io/badge/Code-MIT-blue.svg)](LICENSE)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/Content-CC--BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)

A practical guide to running your applications as systemd services on Linux — with a focus on Raspberry Pi and other embedded systems. Turn any Python or Node.js script into a reliable, self-starting, self-recovering system service.

---

## The Problem This Solves

You build something that works perfectly — a sensor pipeline, an MQTT client, a web server — and then you reboot the device and everything is silent. Nothing started. You SSH in, run your script manually, and it all comes back to life.

That gap between "works when I run it" and "runs automatically and reliably forever" is exactly what systemd fills.

---

## What You'll Learn

How systemd fits into the Linux boot process, how to write a service file from scratch, how to make services restart themselves after crashes, how to declare dependencies so things start in the right order, how to manage configuration and secrets through environment files, how to read and filter service logs, and how to replace cron jobs with systemd timers.

---

## Tutorial Structure

Work through the documents in order if you're new to systemd. If you have some experience, jump to the section you need.

| # | Document | What it covers |
|---|----------|----------------|
| 01 | [What is systemd?](docs/01-what-is-systemd.md) | The boot process, unit files, systemctl, journalctl |
| 02 | [Your First Service](docs/02-your-first-service.md) | Writing and activating a minimal service file |
| 03 | [Restart Policies & Dependencies](docs/03-restart-and-dependencies.md) | Surviving crashes, ordering startup correctly |
| 04 | [Environment & Working Directory](docs/04-environment-and-directory.md) | Config files, secrets, working paths |
| 05 | [Logging with journald](docs/05-logging.md) | Reading logs, filtering, managing disk usage |
| 06 | [Practical Examples](docs/06-examples.md) | Python service, Node.js service, env vars, timers |
| 07 | [Troubleshooting](docs/07-troubleshooting.md) | Common errors and how to diagnose them |

---

## Quick Start

If you just want to get a Python script running as a service as fast as possible:

**Step 1 — Create the service file:**

```bash
sudo nano /etc/systemd/system/my-app.service
```

```ini
[Unit]
Description=My Application
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/my-app
ExecStart=/usr/bin/python3 /home/pi/my-app/main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Step 2 — Enable and start it:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-app.service
sudo systemctl start my-app.service
```

**Step 3 — Check it's running:**

```bash
sudo systemctl status my-app.service
```

---

## Ready-to-Use Examples

All example service files and application scripts live in the [`examples/`](examples/) folder:

- [`python-service/`](examples/python-service/) — A Python script registered as a systemd service
- [`nodejs-service/`](examples/nodejs-service/) — A Node.js application registered as a service
- [`env-service/`](examples/env-service/) — A service that loads secrets from an environment file
- [`timer-service/`](examples/timer-service/) — A systemd timer that runs a script on a schedule

---

## Requirements

- Any Linux system using systemd (Raspberry Pi OS, Ubuntu, Debian, Fedora, and most others)
- Tested on Raspberry Pi OS Bookworm and Ubuntu 22.04+
- Python 3 for the Python examples
- Node.js 18+ for the Node.js example (`sudo apt install nodejs`)

---

## Compatibility Note

Every concept here works on any modern Linux distribution that uses systemd — which is virtually all of them. The examples use `User=pi` and paths like `/home/pi/` because the primary audience is Raspberry Pi users, but substituting your own username and paths works identically on Ubuntu, Debian, Fedora, or any other systemd-based distro.

---

## License

**Code** (all `.py`, `.js`, `.service`, `.timer` files) — [MIT License](LICENSE)
**Tutorial content** (all `.md` files and written documentation) — [CC BY-NC 4.0](LICENSE)

Code is free to use in your own projects without restriction.
The written tutorials may be shared and adapted for non-commercial purposes with attribution. They may not be repackaged or sold.

© 2025 [Supun Akalanka Sriyananda]
