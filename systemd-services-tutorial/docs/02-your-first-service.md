# 02 — Your First Service

This document walks you through creating a real, working service file from scratch. By the end you will have a Python script registered with systemd, starting at boot, and showing up cleanly in `systemctl status`. Every single line of the service file is explained so you understand not just what to type but why it is there.

---

## The Application We Are Registering

For this example, suppose you have a Python script at `/home/pi/my-app/main.py`. The specific content of the script does not matter much for learning systemd — what matters is that it is a long-running process (something that loops, listens for connections, or monitors sensors) rather than a script that runs once and exits.

If you want a concrete working example to follow along with, use the script from [`examples/python-service/hello_service.py`](../examples/python-service/hello_service.py) in this repository. It is a simple loop that logs a heartbeat message every ten seconds — simple enough to understand at a glance, but long-running enough to behave like a real service.

---

## Where Service Files Live

Service files belong in `/etc/systemd/system/`. This directory is specifically reserved for service files that you write and manage yourself — it is separate from the directories where systemd's own built-in services live, and it is separate from the directories that package managers use. Putting your files here means they will not be overwritten by a system update, and they will take precedence over any lower-priority defaults.

The file must have a `.service` extension. The name you give it becomes the name you use with `systemctl`, so choose something short and descriptive. In this tutorial we will use `my-app.service`.

---

## The Minimal Service File

Create the file with:

```bash
sudo nano /etc/systemd/system/my-app.service
```

Type or paste the following:

```ini
[Unit]
Description=My Application

[Service]
ExecStart=/usr/bin/python3 /home/pi/my-app/main.py

[Install]
WantedBy=multi-user.target
```

That is the absolute minimum. Let us go through every line because each one is doing something specific.

### The [Unit] Section

The `[Unit]` section contains metadata and, later, dependency declarations. Right now we only have one line:

`Description=My Application` is a plain-English label that appears whenever you inspect this service — in `systemctl status`, in journal logs, in any system monitoring tool. Write something that will help you identify the service at a glance six months from now. "My Application" is fine for learning, but in a real project you would write something like "Temperature Sensor Data Pipeline" or "MQTT Edge Client".

### The [Service] Section

The `[Service]` section is the core of the file. This is where you tell systemd how to actually run your application.

`ExecStart=/usr/bin/python3 /home/pi/my-app/main.py` is the command that launches your program. A critical rule here is that **you must use the full, absolute path to every executable**. You cannot write `python3 main.py` because systemd does not use your shell's PATH environment. It needs to know the exact location of the Python interpreter. You can find it with `which python3` in your terminal — on most Raspberry Pi systems it will be `/usr/bin/python3`. The path to your script must also be absolute.

### The [Install] Section

The `[Install]` section controls how this service plugs into systemd's startup sequence.

`WantedBy=multi-user.target` is the most important line in this section and deserves a proper explanation. systemd organises the boot process into **targets**, which are milestones that represent specific states of the system. `multi-user.target` represents the state where the system is fully booted, all essential hardware is initialised, networking is available, and the system is ready for normal use — but before any graphical desktop environment starts. It is essentially the "everything is ready, start normal services" point in the boot sequence. By declaring `WantedBy=multi-user.target`, you are saying "start my service when the system reaches this state." This is the correct target for the vast majority of application services.

---

## Activating the Service

Writing the file is not enough on its own. You need to go through two steps: telling systemd the file exists, and then enabling it.

### Step 1: Reload systemd's Configuration

```bash
sudo systemctl daemon-reload
```

systemd reads unit files when it starts and caches their contents. When you create or modify a service file, systemd does not automatically notice the change. Running `daemon-reload` tells it to re-scan all unit file directories and update its internal cache. **You must run this every time you create or edit a service file**, or your changes will be silently ignored.

### Step 2: Enable the Service

```bash
sudo systemctl enable my-app.service
```

This creates a symbolic link inside the `multi-user.target.wants/` directory that points to your service file. That symlink is what causes systemd to start your service at boot. You can actually see it after running enable:

```bash
ls -la /etc/systemd/system/multi-user.target.wants/ | grep my-app
```

### Step 3: Start the Service Now

Enabling only affects future boots. To start the service in the current session without rebooting:

```bash
sudo systemctl start my-app.service
```

In practice, when you are deploying a new service, you will almost always run all three commands in sequence:

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-app.service
sudo systemctl start my-app.service
```

---

## Verifying it is Running

```bash
sudo systemctl status my-app.service
```

If everything is working, the output will look something like this:

```
● my-app.service - My Application
     Loaded: loaded (/etc/systemd/system/my-app.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-16 10:30:00 GMT; 5s ago
   Main PID: 1234 (python3)
      Tasks: 1 (limit: 4164)
     Memory: 12.3M
        CPU: 0.123s
     CGroup: /system.slice/my-app.service
             └─1234 /usr/bin/python3 /home/pi/my-app/main.py
```

The most important line is `Active: active (running)`. The word `enabled` next to `Loaded` confirms it will also start at boot. If you see `active (dead)` it means the service ran and exited — which could be correct if your script exits cleanly, or a problem if you expected it to keep running. If you see `failed`, the status output usually includes the last few lines of log output pointing to the cause.

---

## Testing Reboot Persistence

The real test of a service is whether it survives a reboot:

```bash
sudo reboot
```

After the Pi comes back up, check the status again:

```bash
sudo systemctl status my-app.service
```

If it shows `active (running)` with a start time matching the current boot, your service is working correctly as a persistent, auto-starting system service.

---

## One-Line Enable + Start Shortcut

On newer versions of systemd (v220 and later, which includes all current Raspberry Pi OS versions), you can combine enable and start into a single command with the `--now` flag:

```bash
sudo systemctl enable --now my-app.service
```

This is functionally identical to running `enable` and `start` separately and is slightly more convenient.

---

## What This Minimal Service is Missing

The service you have right now works, but it is missing several things that matter for real-world use. If the application crashes, systemd will leave it dead and never restart it. If you are writing relative file paths in your Python code, they will likely fail because systemd starts services from the root directory, not your project folder. If you have any configuration — API keys, database passwords, server addresses — there is no good place to put them yet.

The next two documents address all of these. Before you move on, though, take a moment to try breaking the service intentionally — force-kill the Python process with `kill <PID>` and then run `systemctl status` to see what systemd does. Observing this default behaviour will make the value of the restart policies in the next document much more concrete.

**Next: [03 — Restart Policies and Dependencies](03-restart-and-dependencies.md)**
