<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 01 — What is systemd?

Before writing your first service file, it's worth spending a few minutes on what systemd actually is and why it exists. The configuration you write later will feel logical rather than arbitrary — you'll understand not just *what* to write but *why*. This is all conceptual, nothing to run yet.

---

## The Boot Process in Plain English

When you power on a Raspberry Pi (or any Linux computer), a very specific sequence of events unfolds. The processor runs a tiny piece of firmware stored in ROM, which locates the bootloader on your SD card. The bootloader loads the Linux kernel into memory and starts it. The kernel then initialises hardware — memory, filesystems, device drivers — and at the very end of this setup phase, it needs to hand control over to the rest of the operating system.

The kernel does this by starting exactly one process and giving it process ID 1. This process is the **init system**, and it becomes the parent of everything else that runs on the machine. On virtually every modern Linux distribution — Raspberry Pi OS, Ubuntu, Debian, Fedora — that process is `systemd`.

From the moment systemd starts, it's in charge. It reads configuration files called **unit files** that describe everything the system needs to do: mount filesystems, configure the network, start background services, bring up the desktop environment. It does all of this in a carefully ordered, parallelised way that's much faster and more reliable than the older shell-script-based init systems it replaced.

The key insight for you as a developer: **if you want your application to be part of that startup sequence — to be managed, monitored, and restarted by the system itself — you just need to write a unit file that describes it.** Once systemd knows about your application, it treats it like any other first-class system component.

---

## Unit Files: Configuration for Everything

systemd manages everything through **unit files** — small, structured text files that follow a consistent format. The one you'll work with most is the **service unit**, which describes a long-running process (a daemon). Other types include **timer units** (for scheduled tasks, covered in the examples section), **socket units** (for socket-activated services), and **mount units** (for filesystem mounts).

All service unit files share the same three-section structure:

```ini
[Unit]
# Metadata, description, and dependency declarations

[Service]
# How to start, stop, and manage the actual process

[Install]
# How this service integrates into the system boot targets
```

You'll become familiar with each of these sections throughout this tutorial. The important thing to know now is that systemd reads these files from `/etc/systemd/system/` — that's where you'll put your own service files. Files in this directory take precedence over systemd's built-in defaults, and they survive package updates, which is exactly what you want for your custom services.

---

## The Two Essential Tools: systemctl and journalctl

You interact with systemd through two command-line tools you'll use constantly. Understanding what each one does before you need them saves a lot of confusion.

**`systemctl`** is the control interface for systemd — how you start, stop, enable, disable, and inspect services. The most important thing to understand is the difference between two pairs of concepts that trip up almost everyone starting out.

The first pair is **start vs enable**. `systemctl start` launches a service *right now*, in the current session. If you reboot, it won't start again unless you've also enabled it. `systemctl enable` creates a symbolic link that tells systemd to start the service at boot — but it doesn't start it right now. In everyday use you almost always want to run both commands together after creating a new service.

The second pair is **stop vs disable**. `systemctl stop` stops a running service immediately, but it'll start again at the next reboot if it's enabled. `systemctl disable` removes the boot-time symlink so it won't start at the next reboot, but it doesn't stop the currently running instance. In practice you often want both when removing a service.

**`journalctl`** is your window into the logs that systemd collects from every service it manages. Rather than writing to scattered text files in `/var/log/`, systemd captures everything your service prints to stdout and stderr and stores it in a structured binary database called the **journal**. This makes filtering, searching, and correlating logs across services much more powerful than traditional log files.

The commands you'll use most often: `journalctl -u my-app.service` shows all historical logs for a specific service. Adding `-f` follows the log in real time, like `tail -f`. Adding `-b` shows only logs from the current boot.

---

## Why This Matters for Embedded Systems

If you're running a Raspberry Pi as a headless embedded device — a sensor node, a home automation hub, an edge computing device — the consequences of your application crashing silently and never restarting are serious. On a device sitting in a remote location or inside a piece of equipment, you might not notice for hours, days, or weeks.

The alternatives people often reach for first — putting commands in `/etc/rc.local`, using `cron @reboot`, or writing shell scripts in `/etc/init.d/` — all work after a fashion, but they give you almost none of the reliability features systemd provides out of the box. They don't automatically restart crashed processes. They don't provide ordered startup relative to hardware and network dependencies. They don't capture logs in a queryable, structured way. They don't give you a clean interface for checking whether your application is actually running and healthy.

systemd gives you all of that, and all it costs is learning how to write a service file. The rest of this tutorial teaches you exactly that, building from the simplest possible example up to a production-grade configuration.

**Next: [02 — Your First Service](02-your-first-service.md)**
