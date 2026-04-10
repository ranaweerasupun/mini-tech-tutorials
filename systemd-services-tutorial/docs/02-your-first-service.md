<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 02 — Your First Service

Let's create a real, working service file from scratch. By the end you'll have a Python script registered with systemd, starting at boot, and showing up cleanly in `systemctl status`. Every line of the service file is explained so you understand not just what to type but why it's there.

---

## The Application We're Registering

For this example, suppose you have a Python script at `/home/pi/my-app/main.py`. The specific content doesn't matter much for learning systemd — what matters is that it's a long-running process (something that loops, listens for connections, or monitors sensors) rather than a script that runs once and exits.

If you want a concrete working example to follow along with, use the script from [`examples/python-service/hello_service.py`](../examples/python-service/hello_service.py) in this repository. It's a simple loop that logs a heartbeat message every ten seconds — straightforward enough to understand at a glance, but long-running enough to behave like a real service.

---

## Where Service Files Live

Service files belong in `/etc/systemd/system/`. This directory is specifically reserved for service files you write and manage yourself — separate from the directories where systemd's own built-in services live, and separate from the directories package managers use. Putting your files here means they won't be overwritten by a system update, and they'll take precedence over any lower-priority defaults.

The file must have a `.service` extension. The name you give it becomes the name you use with `systemctl`, so choose something short and descriptive. In this tutorial we'll use `my-app.service`.

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

That's the absolute minimum. Here's what every line is doing.

### The [Unit] Section

`Description=My Application` is a plain-English label that appears whenever you inspect this service — in `systemctl status`, in journal logs, in any system monitoring tool. Write something that'll help you identify the service at a glance six months from now. "My Application" is fine for learning, but in a real project write something like "Temperature Sensor Data Pipeline" or "MQTT Edge Client".

### The [Service] Section

`ExecStart=/usr/bin/python3 /home/pi/my-app/main.py` is the command that launches your program. A critical rule: **you must use the full, absolute path to every executable**. You can't write `python3 main.py` because systemd doesn't use your shell's PATH environment — it needs to know the exact location of the Python interpreter. Find it with `which python3` in your terminal. On most Raspberry Pi systems it'll be `/usr/bin/python3`. The path to your script must also be absolute.

### The [Install] Section

`WantedBy=multi-user.target` deserves a proper explanation. systemd organises the boot process into **targets** — milestones that represent specific states of the system. `multi-user.target` represents the state where the system is fully booted, all essential hardware is initialised, networking is available, and the system is ready for normal use — but before any graphical desktop starts. It's essentially the "everything is ready, start normal services" point in the boot sequence. By declaring `WantedBy=multi-user.target`, you're saying "start my service when the system reaches this state." This is the correct target for the vast majority of application services.

---

## Activating the Service

Writing the file isn't enough on its own. You need to tell systemd the file exists, then enable it.

### Step 1: Reload systemd's Configuration

```bash
sudo systemctl daemon-reload
```

systemd reads unit files when it starts and caches their contents. When you create or modify a service file, systemd doesn't automatically notice the change. Running `daemon-reload` tells it to re-scan all unit file directories and update its internal cache. **You must run this every time you create or edit a service file**, or your changes will be silently ignored. This is probably the most common gotcha for people new to systemd.

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

In practice, when deploying a new service, you'll almost always run all three commands in sequence:

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-app.service
sudo systemctl start my-app.service
```

---

## Verifying it's Running

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

The most important line is `Active: active (running)`. The word `enabled` next to `Loaded` confirms it'll also start at boot. If you see `active (dead)`, the service ran and exited — which could be correct if your script exits cleanly, or a problem if you expected it to keep running. If you see `failed`, the status output usually includes the last few log lines pointing to the cause.

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

On newer versions of systemd (v220 and later, which includes all current Raspberry Pi OS versions), you can combine enable and start with the `--now` flag:

```bash
sudo systemctl enable --now my-app.service
```

Functionally identical to running `enable` and `start` separately, just more convenient.

---

## What This Minimal Service is Missing

The service you have right now works, but it's missing several things that matter for real-world use. If the application crashes, systemd will leave it dead and never restart it. If you're writing relative file paths in your Python code, they'll likely fail because systemd starts services from the root directory, not your project folder. If you have any configuration — API keys, database passwords, server addresses — there's no good place to put them yet.

The next two documents address all of these. Before you move on though, try breaking the service intentionally — force-kill the Python process with `kill <PID>` and then run `systemctl status` to see what systemd does. Observing this default behaviour makes the value of the restart policies in the next document much more concrete.

**Next: [03 — Restart Policies and Dependencies](03-restart-and-dependencies.md)**
