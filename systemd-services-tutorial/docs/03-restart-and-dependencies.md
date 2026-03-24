# 03 — Restart Policies and Dependencies

The minimal service from the previous document starts your application at boot, but it has a significant weakness: if the application crashes, systemd simply leaves it in a failed state and moves on. For a device running unattended in the field — something you might not physically access for weeks — a silent crash that is never recovered from is unacceptable. This document covers the two additions that transform a basic service into a resilient one: restart policies and dependency declarations.

---

## Restart Policies: Surviving Crashes

The `Restart` directive in the `[Service]` section tells systemd what to do when your application's process exits. Without it, the default behaviour is `Restart=no` — systemd does nothing. Your service just stays dead.

There are several possible values, but in practice you will almost always choose between two of them based on a simple question: should this service restart if you deliberately stop it with `systemctl stop`?

`Restart=on-failure` means: restart the service if the process exits with a non-zero exit code, is killed by a signal, or hits a timeout — but *not* if it exits cleanly with exit code 0. The practical consequence is that `systemctl stop` works cleanly and does not trigger a restart, because systemd sends a clean termination signal which your application handles gracefully. This is the right choice for most production services because it means you can stop a service for maintenance without a restart loop fighting you.

`Restart=always` means: restart no matter what, even if the process exits with code 0. This is appropriate for services that should *never* be down — where even a clean exit is considered abnormal. It is less common but useful for things like a watchdog process or a service whose restart you want explicit control over from systemd alone.

For the vast majority of embedded applications, `on-failure` is the correct choice.

### The RestartSec Pairing

You should always pair `Restart` with `RestartSec`, which sets the delay in seconds before systemd attempts to restart the process. Without it, systemd restarts immediately. This sounds desirable, but it creates a subtle problem: if your service is crashing because a dependency it needs is not yet ready — the network stack is still initialising, or a database is still starting up — an immediate restart will just crash again immediately, and again, and again. Even a small delay of five seconds gives the rest of the system time to settle into a stable state.

```ini
Restart=on-failure
RestartSec=5
```

### Preventing Infinite Crash Loops

Now consider a more serious scenario: your service has a genuine bug that makes it crash immediately on every startup — perhaps a malformed configuration file or a missing Python dependency. Without any limits, systemd will restart it, watch it crash, restart it, watch it crash, forever. This consumes CPU, floods your logs with crash reports, and masks the real problem.

The `StartLimitIntervalSec` and `StartLimitBurst` directives work together to prevent this. `StartLimitBurst` defines the maximum number of restart attempts allowed, and `StartLimitIntervalSec` defines the time window in which those attempts are counted. If the service restarts more than `StartLimitBurst` times within `StartLimitIntervalSec` seconds, systemd declares the service as failed and stops trying.

```ini
StartLimitIntervalSec=60
StartLimitBurst=5
```

With these settings, systemd will make up to five restart attempts within any 60-second window. If the sixth crash happens within that window, it marks the service as failed and stops. At that point `systemctl status` clearly shows that the restart limit was reached, which is a meaningful signal: something is fundamentally broken and needs human attention, not more restart attempts. This is far better than an infinite loop that hides the real problem.

Think of `StartLimitBurst` as a circuit breaker. In electrical engineering, a circuit breaker trips when it detects a fault — it does not keep trying to send power through a short circuit. systemd's start limit is the same idea: try a reasonable number of times, then stop and let a human investigate rather than hammering a broken process indefinitely.

---

## Dependency Declarations: Starting in the Right Order

Most real applications do not run in isolation. An MQTT client is useless if it tries to connect before the network interface exists. A database-backed service will crash if the database process has not finished starting. A camera streaming service needs the camera hardware to be initialised. systemd lets you express these dependencies explicitly, so your service starts at the right moment in the boot sequence rather than just racing against everything else.

The two most important dependency directives live in the `[Unit]` section.

### After: Ordering Without Hard Requirements

`After=some.target` tells systemd not to start your service until `some.target` has been reached. This is purely about *ordering* — it does not create a hard requirement. If `some.target` fails entirely, your service still starts after it in the sequence; it just may find that what it was waiting for is not actually available.

The target you will use most often is `network.target`, which represents the point in the boot sequence where the network subsystem has been initialised. On Raspberry Pi OS, this typically means the kernel network stack is ready and configured interfaces have been brought up.

```ini
After=network.target
```

A more reliable option for network-dependent services — particularly those that connect to remote hosts — is `network-online.target`, which does not just wait for the network subsystem to initialise but waits until at least one network interface has an active connection and is reachable. This is more conservative and means a slightly longer boot time, but it prevents the common failure mode where your service starts, tries to open a TCP connection to a remote server, fails because the network is still negotiating a DHCP address, and then crashes before the restart delay kicks in.

```ini
After=network-online.target
```

### Wants and Requires: Soft and Hard Dependencies

`Wants=some.target` and `Requires=some.target` declare what your service *needs*, not just what it should start *after*. The difference between them is what happens when the dependency is not available.

`Wants` is a soft dependency. If `some.target` is not available or fails to start, systemd will still attempt to start your service. Think of `Wants` as "I would prefer this to be available, but I can try to run without it." This is appropriate when your application has internal handling for the dependency not being there — for example, an MQTT client that queues messages offline when the broker is unreachable.

`Requires` is a hard dependency. If `some.target` fails to start, systemd will not start your service either. Furthermore, if `some.target` is stopped while your service is running, systemd will also stop your service. This is appropriate when your service genuinely cannot function at all without the dependency — for example, a service that reads from a database where the database is also managed by systemd.

In practice, the combination you will use most often for network-dependent services is:

```ini
After=network.target
Wants=network.target
```

This says "start after the network is ready, and express a preference for it to be available — but if the network fails, keep my service running, because I handle network loss internally."

---

## The Updated Service File

Putting the restart policy and dependency declarations together, here is the service file updated from the minimal version in the previous document:

```ini
[Unit]
Description=My Application
After=network.target
Wants=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/my-app/main.py
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
```

After editing the file, remember to reload systemd and restart the service to apply the changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart my-app.service
```

You can test the restart policy right now without rebooting. Find the process ID of your running service from `systemctl status`, then kill it:

```bash
sudo kill -9 <PID>
```

Wait five seconds and then run `systemctl status` again. You should see the service back in `active (running)` state with a new PID and a note that it was restarted. That automatic recovery is exactly what you want from a service running unattended in the field.

---

## Common Dependency Targets Reference

Beyond `network.target`, there are a handful of other targets that come up regularly in embedded service files. `local-fs.target` ensures all local filesystems are mounted — useful if your service reads or writes files on a specific mount point. `time-sync.target` ensures the system clock has been synchronised via NTP, which matters for any service that timestamps data or signs tokens. `bluetooth.target` ensures the Bluetooth subsystem is available, relevant for Raspberry Pi projects that communicate with BLE devices. For services that depend on another service you have written yourself, you can declare `After=my-other-app.service` and `Requires=my-other-app.service` directly by service name.

**Next: [04 — Environment Variables and Working Directory](04-environment-and-directory.md)**
