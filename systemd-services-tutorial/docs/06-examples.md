# 06 — Practical Examples

This document walks through four complete, working examples that put everything from the previous sections into practice. Each example includes a full service file with every line explained, along with the application script it manages. All source files are in the [`examples/`](../examples/) folder of this repository.

---

## Example 1: Python Script as a Service

This is the most common starting point. The example runs a Python script that logs a heartbeat message every ten seconds — simple enough to understand immediately, but structured like a real long-running service.

The application script at `examples/python-service/hello_service.py` uses Python's `logging` module to write structured messages to stdout, which systemd captures into the journal automatically.

```python
# examples/python-service/hello_service.py
import logging
import time
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Service starting up")
    counter = 0
    while True:
        counter += 1
        logger.info(f"Heartbeat #{counter} — service is alive")
        time.sleep(10)

if __name__ == "__main__":
    main()
```

The service file at `examples/python-service/hello-python.service` is a complete configuration incorporating everything covered in this tutorial:

```ini
[Unit]
Description=Python Heartbeat Service (Tutorial Example)
After=network.target
Wants=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/systemd-services-tutorial/examples/python-service
ExecStart=/usr/bin/python3 hello_service.py
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hello-python

[Install]
WantedBy=multi-user.target
```

To deploy this example, copy the service file to the system directory, then enable and start it:

```bash
sudo cp examples/python-service/hello-python.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hello-python.service
```

Verify it is running and watch the heartbeat messages appear:

```bash
sudo systemctl status hello-python.service
journalctl -u hello-python.service -f
```

---

## Example 2: Node.js Application as a Service

The exact same systemd concepts apply to any language or runtime — Python is not special here. This example shows a minimal Node.js HTTP server registered as a service, demonstrating that the service file structure is essentially identical regardless of what language runs underneath.

The application at `examples/nodejs-service/server.js` is a small HTTP server that responds to every request with a timestamp:

```javascript
// examples/nodejs-service/server.js
const http = require("http");

const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || "0.0.0.0";

const server = http.createServer((req, res) => {
  const message = `Hello from systemd! Server time: ${new Date().toISOString()}\n`;
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end(message);
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
});

server.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});

// Handle graceful shutdown when systemd sends SIGTERM
process.on("SIGTERM", () => {
  console.log("Received SIGTERM — shutting down gracefully");
  server.close(() => {
    console.log("Server closed. Goodbye.");
    process.exit(0);
  });
});
```

The SIGTERM handler is worth paying attention to. When you run `systemctl stop`, systemd sends a SIGTERM signal to the process, giving it a chance to shut down cleanly before it is force-killed. Without this handler, Node.js would terminate abruptly — dropping any in-flight requests and potentially leaving resources in an inconsistent state. The handler here closes the HTTP server gracefully before exiting, which is the correct way to handle shutdown for any network service.

The service file at `examples/nodejs-service/hello-node.service` looks almost identical to the Python version, with only the `ExecStart` command changed:

```ini
[Unit]
Description=Node.js HTTP Server (Tutorial Example)
After=network.target
Wants=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/systemd-services-tutorial/examples/nodejs-service

# PORT and HOST can be overridden here without touching the application code
Environment="PORT=3000"
Environment="HOST=0.0.0.0"

ExecStart=/usr/bin/node server.js
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hello-node

# Give the server 15 seconds to finish handling existing connections before force-killing
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

`TimeoutStopSec=15` is a useful addition for any network server. It tells systemd to wait up to 15 seconds after sending SIGTERM before giving up and sending SIGKILL. This gives the SIGTERM handler in `server.js` time to finish handling active connections before the process is force-killed.

Find the path to Node.js on your system with `which node`. On Raspberry Pi OS installed via `apt`, it is typically `/usr/bin/node`. If you installed Node.js via `nvm` or another version manager, use the full path to that installation's node binary instead.

---

## Example 3: A Service that Reads an Environment File

This example shows the complete workflow for managing a service that needs secrets — database credentials, API keys, authentication tokens — without ever putting those values inside the service file itself.

The application at `examples/env-service/app_with_config.py` reads several environment variables, validates that the required ones are present, and logs what it received:

```python
# examples/env-service/app_with_config.py
import os
import logging
import time
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

def load_config():
    """Load and validate required environment variables."""
    required = ["API_KEY", "BROKER_HOST"]
    missing  = [key for key in required if not os.environ.get(key)]

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Check /etc/env-service/config.env and restart the service.")
        sys.exit(1)    # Non-zero exit triggers Restart=on-failure

    return {
        "api_key":     os.environ["API_KEY"],
        "broker_host": os.environ["BROKER_HOST"],
        "broker_port": int(os.environ.get("BROKER_PORT", "1883")),
        "log_level":   os.environ.get("LOG_LEVEL", "INFO"),
    }

def main():
    config = load_config()
    logger.info("Configuration loaded successfully")
    # Deliberately not logging the API key — never log secrets
    logger.info(f"Broker: {config['broker_host']}:{config['broker_port']}")
    logger.info(f"Log level: {config['log_level']}")

    while True:
        logger.info("Working with loaded configuration...")
        time.sleep(15)

if __name__ == "__main__":
    main()
```

The environment file lives at `/etc/env-service/config.env` with restricted permissions so only root can read it:

```bash
# Create the directory and file
sudo mkdir -p /etc/env-service
sudo nano /etc/env-service/config.env
```

The file contents follow a simple KEY=VALUE format:

```bash
# /etc/env-service/config.env
BROKER_HOST=mqtt.example.com
BROKER_PORT=8883
API_KEY=replace-with-your-actual-key
LOG_LEVEL=INFO
```

Restrict access immediately after creating it:

```bash
sudo chmod 600 /etc/env-service/config.env
sudo chown root:root /etc/env-service/config.env
```

The service file at `examples/env-service/env-example.service` references this file:

```ini
[Unit]
Description=Service with Environment File (Tutorial Example)
After=network.target
Wants=network.target

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/systemd-services-tutorial/examples/env-service

# Load secrets from a separately protected file
# The leading '-' means: if the file is missing, log a warning but still start
EnvironmentFile=-/etc/env-service/config.env

ExecStart=/usr/bin/python3 app_with_config.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=env-service

[Install]
WantedBy=multi-user.target
```

One thing to appreciate about this pattern: if you ever need to rotate a credential — update an API key, change a database password — you edit only `/etc/env-service/config.env`, then restart the service with `sudo systemctl restart env-service.service`. You never touch the service file itself, and the new values are picked up immediately on restart.

---

## Example 4: Scheduled Tasks with systemd Timers

This is arguably the most useful thing in this entire tutorial for embedded systems developers. A **systemd timer** is the modern replacement for cron — it runs a service on a schedule, but with all of systemd's dependency handling, logging, and error management baked in. When a cron job fails silently, you often do not know for days. When a timer-triggered service fails, it shows up in `systemctl status` and `journalctl` exactly like any other failed service.

A timer in systemd is actually two unit files working together: a `.service` file that describes what to run, and a `.timer` file that describes when to run it.

The application at `examples/timer-service/cleanup.py` is a maintenance script that deletes files older than a configurable number of days from a specific directory — a realistic task that many embedded devices need to run periodically to avoid filling up storage:

```python
# examples/timer-service/cleanup.py
import os
import time
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)
logger = logging.getLogger(__name__)

TARGET_DIR  = os.environ.get("CLEANUP_DIR",  "/home/pi/data")
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS", "7"))

def main():
    if not os.path.isdir(TARGET_DIR):
        logger.warning(f"Target directory does not exist: {TARGET_DIR}")
        return

    cutoff   = time.time() - (MAX_AGE_DAYS * 86400)
    removed  = 0
    errors   = 0

    for filename in os.listdir(TARGET_DIR):
        filepath = os.path.join(TARGET_DIR, filename)
        try:
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                logger.info(f"Removed old file: {filename}")
                removed += 1
        except OSError as e:
            logger.error(f"Could not remove {filename}: {e}")
            errors += 1

    logger.info(f"Cleanup complete: {removed} file(s) removed, {errors} error(s)")

if __name__ == "__main__":
    main()
```

The service file at `examples/timer-service/cleanup.service` describes what to run. Notice that it has no `[Install]` section and no `WantedBy` — it is activated exclusively by the timer, not by a boot target:

```ini
[Unit]
Description=Periodic File Cleanup Task

[Service]
User=pi
Group=pi
Type=oneshot
WorkingDirectory=/home/pi/systemd-services-tutorial/examples/timer-service
Environment="CLEANUP_DIR=/home/pi/data"
Environment="MAX_AGE_DAYS=7"
ExecStart=/usr/bin/python3 cleanup.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cleanup-task
```

`Type=oneshot` is important here. It tells systemd that this service is expected to start, run to completion, and exit — rather than run as a long-running daemon. Systemd waits for the process to exit before considering the service "done," which ensures the timer does not fire again while a previous run is still in progress.

The timer file at `examples/timer-service/cleanup.timer` describes when to run the service. It must have the same base name as the service file:

```ini
[Unit]
Description=Run File Cleanup Every Day at 3 AM

[Timer]
# Run at 3:00 AM every day
OnCalendar=*-*-* 03:00:00

# If the system was off when the timer was supposed to fire,
# run it shortly after the next boot to catch up
Persistent=true

# Wait until the system has been up for 5 minutes before firing
# (avoids running heavy tasks during the busy boot period)
OnBootSec=5min

[Install]
WantedBy=timers.target
```

`Persistent=true` is an excellent feature for embedded devices that might be powered off during scheduled windows. If your Raspberry Pi is switched off at 3 AM when the cleanup was supposed to run, systemd will note the missed run and execute it shortly after the device next boots. Without `Persistent=true`, missed runs are simply skipped.

The `OnCalendar` syntax is flexible and readable. Some useful examples: `daily` runs once per day at midnight, `weekly` runs once per week on Monday at midnight, `hourly` runs at the top of every hour, `Mon *-*-* 09:00:00` runs every Monday at 9 AM, and `*-*-* 00/6:00:00` runs every 6 hours.

To deploy the timer example, both files need to be copied and the timer (not the service) needs to be enabled:

```bash
sudo cp examples/timer-service/cleanup.service /etc/systemd/system/
sudo cp examples/timer-service/cleanup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cleanup.timer
```

To see all active timers and when they will next fire, run:

```bash
systemctl list-timers
```

To test the service immediately without waiting for the scheduled time, you can trigger it manually:

```bash
sudo systemctl start cleanup.service
journalctl -u cleanup.service -n 20
```

**Next: [07 — Troubleshooting](07-troubleshooting.md)**
