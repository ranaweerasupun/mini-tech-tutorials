# 05 — Logging with journald

One of the most underappreciated benefits of running your application as a systemd service is that you get a powerful, structured logging system essentially for free. Any text your application prints to standard output or standard error is automatically captured, timestamped, and stored in the **journal** — systemd's centralised log database. This document explains how to read, filter, and manage those logs, and how to configure the journal to be a responsible citizen on embedded devices with limited storage.

---

## How systemd Captures Your Logs

When your service is running, systemd intercepts everything written to `stdout` and `stderr` and passes it to `systemd-journald`, the journal daemon. You do not need to change anything in your application code — a plain `print("sensor reading: 42.3")` in Python becomes a structured journal entry with a precise timestamp, the service name, the process ID, and the message text all stored together.

The only service file configuration required to make this explicit is:

```ini
StandardOutput=journal
StandardError=journal
SyslogIdentifier=my-app
```

`StandardOutput=journal` and `StandardError=journal` are actually the defaults in modern systemd, so you do not strictly need to specify them. But being explicit makes the service file self-documenting — anyone reading it can immediately see where the logs go. `SyslogIdentifier` sets a short tag that is attached to every journal entry from this service, making it easy to filter for your specific application even if multiple services share similar names.

---

## Reading Logs with journalctl

The `journalctl` command is your primary interface to the journal. Its most important option for service debugging is `-u`, which filters entries to a specific unit:

```bash
# Show all historical logs for your service
journalctl -u my-app.service

# Follow the log in real time — like 'tail -f' on a log file
journalctl -u my-app.service -f

# Show only logs from the current boot
journalctl -u my-app.service -b

# Show only logs from the previous boot (useful after a crash)
journalctl -u my-app.service -b -1

# Show logs from the last hour
journalctl -u my-app.service --since "1 hour ago"

# Show logs between two specific timestamps
journalctl -u my-app.service --since "2025-12-16 10:00" --until "2025-12-16 11:00"

# Show only error-level and above (useful to find crashes quickly)
journalctl -u my-app.service -p err

# Show the last 50 lines, most recent first
journalctl -u my-app.service -n 50 -r
```

The `-b -1` option is particularly valuable for embedded systems. If your device rebooted unexpectedly — perhaps due to a power cut or a kernel panic — you can look at the logs from the *previous* boot to understand what was happening right before it went down.

---

## Log Priority Levels

systemd's journal understands syslog-compatible priority levels. If your application logs at different severity levels, you can filter journal output to show only entries at or above a certain severity. The levels from most to least severe are `emerg` (0), `alert` (1), `crit` (2), `err` (3), `warning` (4), `notice` (5), `info` (6), and `debug` (7).

From Python, the easiest way to emit prioritised log entries is with the standard `logging` module. When your service runs under systemd, the `logging` module's output goes to stdout, which the journal captures and stores. If you want the journal to recognise the priority of each entry rather than treating everything as `info`, you can use the `systemd` Python bindings or simply structure your output so that log level appears in the message text — both approaches work fine in practice for most embedded applications.

For most embedded projects, the simplest and most readable approach is:

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stdout   # systemd captures stdout to the journal
)

logger = logging.getLogger(__name__)
logger.info("Service started successfully")
logger.warning("Sensor reading out of expected range")
logger.error("Failed to connect to broker — will retry")
```

With this pattern, your log messages are clean and consistent, and you can filter them in the journal by searching for `ERROR` or `WARNING` in the message text with `journalctl -u my-app.service -g "ERROR"`.

---

## Managing Journal Size on Embedded Devices

This is an important practical concern that most tutorials skip. The Raspberry Pi typically uses an SD card for storage, and SD cards have two relevant limitations: they have finite capacity, and they have a limited number of write cycles before they start to fail. By default, systemd's journal will grow to fill a significant fraction of available disk space — which on a small SD card could be many gigabytes. Leaving the journal unconfigured on an embedded device is a recipe for eventually running out of disk space or unnecessarily wearing out the SD card.

The journal daemon is configured in `/etc/systemd/journald.conf`. Open it with:

```bash
sudo nano /etc/systemd/journald.conf
```

Add or uncomment these lines in the `[Journal]` section:

```ini
[Journal]
# Maximum total size of all journal files on disk
SystemMaxUse=50M

# Maximum size of a single journal file
SystemMaxFileSize=10M

# Maximum time to store journal entries (optional, for low-activity devices)
MaxRetentionSec=1month
```

After making changes, restart the journal daemon:

```bash
sudo systemctl restart systemd-journald
```

Fifty megabytes is a reasonable upper bound for most edge devices. It is large enough to retain several days of logs at typical verbosity, and small enough to not be a meaningful strain on a 16GB or 32GB SD card. If your application is particularly chatty — logging hundreds of lines per minute — you may want to reduce this further, or adjust your application's log verbosity before reaching for the journal size limit.

You can check the current journal disk usage at any time with:

```bash
journalctl --disk-usage
```

---

## Viewing Logs Without Paging

By default, `journalctl` opens output in a pager (like `less`) which requires you to press `q` to exit. When you are running quick diagnostic commands over SSH, this can be inconvenient. Add `--no-pager` to get plain terminal output that you can scroll or pipe to `grep`:

```bash
# Print all logs without opening a pager
journalctl -u my-app.service --no-pager

# Find all lines containing "error" (case-insensitive)
journalctl -u my-app.service --no-pager | grep -i error

# Count how many warning lines appeared in the last hour
journalctl -u my-app.service --since "1 hour ago" --no-pager | grep -c WARNING
```

The combination of `journalctl` filtering and standard Unix tools like `grep`, `awk`, and `wc` gives you a surprisingly capable log analysis workflow without needing any additional tooling.

**Next: [06 — Practical Examples](06-examples.md)**
