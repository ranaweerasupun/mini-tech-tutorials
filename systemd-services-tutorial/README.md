# 🔧 systemd Services Tutorial

A beginner-friendly, open-source guide to running your applications as **systemd services** on Linux — with a focus on Raspberry Pi and other embedded systems. Learn how to turn any Python or Node.js script into a reliable, self-starting, self-recovering system service.

---

## The Problem This Solves

You build something that works perfectly — a sensor pipeline, an MQTT client, a web server — and then you reboot the device and everything is silent. Nothing started. You SSH in, run your script manually, and it all comes back to life.

That gap between "works when I run it" and "runs automatically and reliably forever" is exactly what systemd fills.

---

## What You'll Learn

By the end of this tutorial you will understand what systemd is and how it fits into Linux boot, how to write a service file from scratch, how to make services restart themselves after crashes, how to declare dependencies so things start in the right order, how to manage configuration and secrets through environment files, how to read and filter service logs, and how to replace cron jobs with systemd timers.

---

## Tutorial Structure

Work through the documents in order if you are new to systemd. If you have some experience, jump to the section you need.

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
- Node.js 18+ for the Node.js example (install with `sudo apt install nodejs`)

---

## Compatibility Note

Every concept in this tutorial works on any modern Linux distribution that uses systemd — which is virtually all of them. The examples use `User=pi` and paths like `/home/pi/` because the primary audience is Raspberry Pi users, but substituting your own username and paths works identically on Ubuntu, Debian, Fedora, or any other systemd-based distro.

---

## License

Released under the [MIT License](LICENSE). All examples are free to use, adapt, and share.
