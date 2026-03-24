# 04 — Environment Variables and Working Directory

Two practical issues come up almost immediately when you move a real application into a systemd service. The first is that relative file paths break — code that works fine when you run it from your terminal stops finding its own files when systemd runs it. The second is that your application needs some configuration — server addresses, API keys, database credentials — and hardcoding those values into your service file is both inflexible and a security risk. This document solves both problems.

---

## The Working Directory Problem

When you run a Python script from your terminal, your shell sets the working directory to wherever you currently are. If you are in `/home/pi/my-app/` and your script opens `config.json` without a full path, Python looks for `config.json` in `/home/pi/my-app/` and finds it. This is so natural that most developers do not even think about it.

When systemd runs your service, the working directory is not set to your project folder. By default it is `/`, the root of the filesystem. That same `open("config.json")` call will look for `/config.json`, fail with a FileNotFoundError, and crash your service before it has done anything useful.

The fix is the `WorkingDirectory` directive in the `[Service]` section:

```ini
WorkingDirectory=/home/pi/my-app
```

With this set, any relative file paths your application uses will be resolved relative to that directory, just as they would be if you ran the script from that directory in your terminal. While you are at it, it is also good practice to specify which user the service should run as. By default, systemd runs services as `root`, which is more privilege than most applications need and creates a security risk if the application is ever compromised.

```ini
User=pi
Group=pi
WorkingDirectory=/home/pi/my-app
```

Running as a non-root user is a well-established security principle called the **principle of least privilege**: give a process only the permissions it actually needs. If your MQTT client or sensor pipeline has a bug that an attacker could exploit, running as `pi` means the attacker gets the capabilities of the `pi` user — not root access to the entire system. The tradeoff is that you need to ensure the `pi` user has read/write permission to the files and directories your application needs, but that is almost always already the case for files in `/home/pi/`.

---

## Inline Environment Variables

The simplest way to pass configuration to a service is with the `Environment` directive, which sets individual environment variables directly inside the service file:

```ini
[Service]
Environment="APP_PORT=8080"
Environment="LOG_LEVEL=INFO"
Environment="BROKER_HOST=localhost"
```

Your Python code reads these with `os.environ.get("APP_PORT")` or `os.getenv("APP_PORT", "8080")` (the second argument being a default if the variable is not set). This approach is fine for non-sensitive configuration — server addresses, port numbers, feature flags, log verbosity settings. It is clear, explicit, and the values are visible in `systemctl status` output which makes debugging easy.

However, you should never use `Environment` for secrets. API keys, database passwords, authentication tokens — these are sensitive values that should not be visible in service file contents, which can be read by anyone with filesystem access. For secrets, you need an environment file.

---

## Environment Files: The Right Way to Handle Secrets

An **EnvironmentFile** is a separate text file, usually stored in `/etc/` with restricted permissions, that contains key-value pairs which systemd loads and injects into your service's environment before starting it. The service file references the path to this file rather than containing the values themselves.

First, create the directory and the environment file:

```bash
sudo mkdir -p /etc/my-app
sudo nano /etc/my-app/config.env
```

The file format is simple — one variable per line, using the same `KEY=VALUE` syntax you would use in a shell script. Comments starting with `#` are allowed:

```bash
# /etc/my-app/config.env
# Server configuration
BROKER_HOST=mqtt.example.com
BROKER_PORT=8883

# Authentication — keep this file private
API_KEY=your-secret-api-key-here
DB_PASSWORD=your-database-password-here
```

Now restrict the file's permissions so that only root can read it. This is the crucial step that makes this pattern secure: the values are on disk, but only privileged processes can read them.

```bash
sudo chmod 600 /etc/my-app/config.env
sudo chown root:root /etc/my-app/config.env
```

Finally, reference the file in your service with the `EnvironmentFile` directive:

```ini
EnvironmentFile=/etc/my-app/config.env
```

When systemd starts your service, it reads this file and sets all the listed variables in the service's environment. Your Python code reads them with `os.environ.get("API_KEY")` exactly as it would read any other environment variable — it does not need to know where they came from.

A small but important syntax note: if you prefix the path with a minus sign (`-`), systemd will silently ignore a missing file rather than failing to start the service. This is useful during development when the config file may not exist yet:

```ini
EnvironmentFile=-/etc/my-app/config.env
```

---

## The Complete Service File So Far

Combining everything from the last three documents, here is the service file in its current form. This is starting to look like a real production configuration:

```ini
[Unit]
Description=My Application
After=network.target
Wants=network.target

[Service]
# Run as a non-root user for security
User=pi
Group=pi

# Set the working directory so relative paths work correctly
WorkingDirectory=/home/pi/my-app

# Load secrets and configuration from a separate, restricted file
EnvironmentFile=/etc/my-app/config.env

# Non-sensitive configuration can go inline
Environment="LOG_LEVEL=INFO"

# The command that launches your application
ExecStart=/usr/bin/python3 /home/pi/my-app/main.py

# Restart automatically on unexpected crashes
Restart=on-failure
RestartSec=5

# Give up after 5 crashes within 60 seconds — signal a real problem
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
```

After making changes, reload and restart as always:

```bash
sudo systemctl daemon-reload
sudo systemctl restart my-app.service
```

---

## Accessing Environment Variables in Python

To make this concrete, here is how your Python application would read the environment variables set by the service file and environment file:

```python
import os

# Read from EnvironmentFile (secrets)
broker_host = os.environ.get("BROKER_HOST", "localhost")
broker_port = int(os.environ.get("BROKER_PORT", "1883"))
api_key     = os.environ.get("API_KEY")

# Read from inline Environment directive
log_level   = os.environ.get("LOG_LEVEL", "INFO")

if api_key is None:
    # Using print() works fine — systemd captures stdout to the journal
    print("ERROR: API_KEY is not set. Check /etc/my-app/config.env")
    raise SystemExit(1)

print(f"Connecting to {broker_host}:{broker_port} with log level {log_level}")
```

A useful pattern here is to fail fast with a clear, specific error message if a required variable is missing. When systemd captures that error from stdout and logs it to the journal, you will see exactly why the service failed — much better than a cryptic exception from deep inside a library that happens to receive `None` where it expected a string.

**Next: [05 — Logging with journald](05-logging.md)**
