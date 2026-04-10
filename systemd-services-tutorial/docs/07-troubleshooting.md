<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 07 — Troubleshooting

Debugging systemd service issues is a different skill from debugging application code, because the failure can happen in several distinct places: the service file syntax might be wrong, the paths might be incorrect, the user permissions might be insufficient, or the application itself might be crashing for reasons unrelated to systemd. Start from the top and work downward — problems in early steps often cause confusing symptoms that look like problems in later ones.

---

## The Golden Rule: Always Check Status and Logs First

Before trying anything else, run these two commands. Between them, they answer the vast majority of service problems:

```bash
# What is the current state of the service and why?
sudo systemctl status my-app.service

# What did the service print before it failed?
journalctl -u my-app.service -n 50 --no-pager
```

The `status` output tells you whether the service is running, failed, or inactive, and it includes the last few log lines inline. The `journalctl` command gives you the full recent log history. Together they usually point directly to the problem — an incorrect file path, a missing Python module, an unhandled exception, a permission error. Read both outputs carefully before trying any fixes.

---

## Problem: Service Fails to Start — "No such file or directory"

The most common error when first deploying a service. It means systemd can't find something it was pointed to — usually either the Python (or Node.js) interpreter, or your application script itself.

The fix is always the same: verify every path in `ExecStart` individually. Don't trust what you typed — confirm it from the terminal:

```bash
# Does the Python interpreter exist at this exact path?
ls -la /usr/bin/python3

# Does your application script exist at this exact path?
ls -la /home/pi/my-app/main.py
```

If either `ls` command returns "No such file or directory", you've found the problem. For the interpreter path, use `which python3` to find the correct location. For the application script, make sure you're using the absolute path starting from `/`, not a relative path.

A second common cause is that the file exists but the service user doesn't have read or execute permission on it:

```bash
# Check the file permissions
ls -la /home/pi/my-app/main.py

# Check whether the pi user can read it
sudo -u pi cat /home/pi/my-app/main.py
```

If the `cat` command fails with a permission denied error:

```bash
chmod 644 /home/pi/my-app/main.py
```

---

## Problem: Service Starts and Immediately Exits

You run `systemctl start`, it appears to work, but `systemctl status` shows `inactive (dead)` or `failed` rather than `active (running)`. The process started but exited almost immediately.

First check whether your application is actually a long-running process or a script that runs and exits cleanly. A script that processes a file and exits with code 0 is perfectly valid — systemd will mark it as `active (dead)` (the correct status for a `Type=oneshot` service). If you expected it to keep running, your application code may have an early return, an unhandled exception, or a crash on startup.

Read the logs carefully:

```bash
journalctl -u my-app.service --no-pager
```

If you see a Python traceback, an ImportError, or any other exception, that's your problem. Fix the application code first, then re-test. A common cause is that the application works fine when you run it manually as the `pi` user, but crashes when systemd runs it from a different working directory. Always check that `WorkingDirectory` is set correctly and that the service user has the permissions it needs.

---

## Problem: My Changes to the Service File Are Not Taking Effect

You edited the service file, restarted the service, but the old behaviour persists. Almost always caused by forgetting to run `daemon-reload` before restarting.

systemd caches unit file contents at startup and when you explicitly tell it to reload. It doesn't watch for file changes. If you skip `daemon-reload`, systemd restarts the service using the cached version of the file, not the new one you just saved.

The required sequence after any service file edit:

```bash
sudo systemctl daemon-reload
sudo systemctl restart my-app.service
```

Build this into muscle memory. A useful habit is to always run both commands together as a single line so the restart only happens if the reload succeeds:

```bash
sudo systemctl daemon-reload && sudo systemctl restart my-app.service
```

---

## Problem: Service Works Manually But Not as a systemd Service

Your script runs perfectly when you `cd` to the project directory and run `python3 main.py`, but when systemd runs it, things go wrong. The most frequent causes:

**Wrong working directory.** When you run the script manually, your shell sets the working directory to wherever you are. systemd defaults to `/`. Any relative file path in your code — `open("config.json")`, `open("data/readings.csv")` — will fail because systemd is looking from `/`, not from your project directory. Fix: add `WorkingDirectory=/home/pi/my-app` to the `[Service]` section.

**Different environment variables.** Your shell session has many environment variables set — `HOME`, `PATH`, `USER`, and anything you've added to `.bashrc` or `.profile`. systemd services start with a minimal, clean environment, so those variables may not be present. If your application depends on any environment variable set in your shell profile, you need to explicitly add it to the service file with `Environment=` or `EnvironmentFile=`.

**Different Python packages.** If you're using a virtual environment, the Python interpreter in your `venv` has access to packages the system Python doesn't. Make sure `ExecStart` points to the Python interpreter *inside your virtual environment*, not the system Python:

```ini
# Wrong — uses system Python, which may not have your packages
ExecStart=/usr/bin/python3 main.py

# Correct — uses the venv Python, which has all installed packages
ExecStart=/home/pi/my-app/venv/bin/python3 main.py
```

---

## Problem: "Unit not found" When Running systemctl Commands

You run `sudo systemctl status my-app.service` and get "Unit my-app.service could not be found." The service file doesn't exist, is in the wrong location, or hasn't been registered with `daemon-reload` yet.

Check that the file exists in the right place:

```bash
ls -la /etc/systemd/system/my-app.service
```

If the file is there, run `daemon-reload` and try again. If it's not there, either it was never created or it ended up in a different directory. Verify the filename carefully — the extension must be `.service` and the name must match exactly what you're passing to `systemctl`.

---

## Problem: Service Keeps Restarting in a Loop

You check `systemctl status` and see the service repeatedly restarting — a new PID every few seconds, a growing restart count. The application is crashing on startup and the restart policy is bringing it back up only for it to crash again.

Don't be tempted to disable the restart policy as a fix. The restart policy isn't the problem — the application crashing is the problem. Read the logs carefully to find the root cause:

```bash
journalctl -u my-app.service -n 100 --no-pager | grep -iE "error|exception|traceback|failed"
```

Common causes of crash-on-startup: a missing environment variable, a missing or malformed config file, a Python package not installed in the environment the service is using, and a port already in use if you're starting a network server.

Once you've found and fixed the root cause, reset the failure state so systemd will start the service again:

```bash
sudo systemctl reset-failed my-app.service
sudo systemctl start my-app.service
```

---

## Problem: EnvironmentFile Not Found or Variables Missing

If you're using `EnvironmentFile` and the variables aren't being loaded, first verify the file exists and has the correct path:

```bash
ls -la /etc/my-app/config.env
```

Then check its permissions. systemd reads the file as root before spawning the service process, so even if the service runs as `pi`, the file just needs to be readable by root:

```bash
sudo chmod 600 /etc/my-app/config.env
sudo chown root:root /etc/my-app/config.env
```

Also check the file format. Each line must be `KEY=VALUE` with no spaces around the equals sign, and no shell syntax like `export KEY=VALUE`. The `EnvironmentFile` parser is not a shell — it reads simple key-value pairs only.

---

## Useful Diagnostic Commands Reference

```bash
# Full service status and recent logs
sudo systemctl status my-app.service

# Live log stream
journalctl -u my-app.service -f

# All logs since last boot
journalctl -u my-app.service -b --no-pager

# Logs from the boot before last (useful after an unexpected reboot)
journalctl -u my-app.service -b -1 --no-pager

# Verify systemd can parse your service file without errors
systemd-analyze verify /etc/systemd/system/my-app.service

# Check the complete effective configuration that systemd sees
systemctl cat my-app.service

# Show all environment variables the service will have
systemctl show my-app.service -p Environment

# List all failed services on the system
systemctl --failed

# Reset a failed service so it can be started again
sudo systemctl reset-failed my-app.service

# List all active timers and their next fire times
systemctl list-timers
```

The `systemd-analyze verify` command is particularly useful when you have a syntax error in your service file — it catches problems before you deploy, including unknown directives, invalid values, and missing referenced files.
