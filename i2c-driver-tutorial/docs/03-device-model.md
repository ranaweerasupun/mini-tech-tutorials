# 03 — The Linux Device Model

With a working module build environment and a feel for the load/unload cycle, you are ready for the concept that is genuinely the biggest conceptual shift in kernel driver development: the Linux device model. Understanding this model is what separates people who can read kernel driver code from those who cannot, and it explains decisions in the TMP102 driver that would otherwise look arbitrary.

---

## The Problem the Device Model Solves

Imagine you are the kernel, and a USB keyboard has just been plugged in. You need to find a driver for it. How do you do that?

One approach would be for every driver to register itself at boot and then poll for its hardware. But there are thousands of possible devices and hundreds of loaded drivers — having every driver constantly checking if its hardware appeared would be enormously wasteful and chaotic.

The Linux device model solves this with a clean separation of responsibilities. **Devices** describe hardware that exists — a specific chip at a specific address on a specific bus. **Drivers** describe code that can handle a particular type of hardware. A third piece, the **bus subsystem**, sits between them as a matchmaker: when a device appears, the bus subsystem searches for a registered driver that claims to support it. When a driver is registered, the bus subsystem searches for any already-known devices that match. When a match is found, the bus subsystem calls a specific function in the driver to begin the relationship. That function is called `probe`.

This separation is elegant because drivers and devices are genuinely decoupled. A driver does not need to know when or whether its device is present. It simply registers what it supports. The bus subsystem handles the timing.

---

## The Probe Function: The Real Entry Point

In the hello module from the previous document, `hello_init` was your entry point — it ran when the module was loaded. In a device driver, `hello_init` equivalent is almost empty. The real work happens in `probe`.

The `probe` function is called by the kernel's bus subsystem when it has matched your driver to a specific device. It receives a pointer to the device it is about to manage and is responsible for setting everything up: allocating memory for the driver's private state, initialising hardware, and registering with whatever kernel subsystems the driver will use (in our case, the hwmon subsystem for hardware monitoring).

The counterpart is `remove`, which is called when the device goes away — a USB device is unplugged, or a module is unloaded while the device is active. It is responsible for reversing whatever `probe` did.

A minimal I2C driver structure looks like this in code, before any real logic is added:

```c
static int my_driver_probe(struct i2c_client *client,
                           const struct i2c_device_id *id)
{
    dev_info(&client->dev, "Device found at address 0x%02x\n",
             client->addr);
    return 0;   /* 0 = success, probe worked */
}

static int my_driver_remove(struct i2c_client *client)
{
    dev_info(&client->dev, "Device removed\n");
    return 0;
}
```

Notice `dev_info()` instead of `pr_info()`. The `dev_*` family of logging functions is preferred in drivers because it automatically prefixes the log message with the device's name and location — you will see messages like `tmp102 1-0048: TMP102 found!` in `dmesg`, where `1-0048` tells you exactly which bus and address this particular device is on. This makes multi-device systems much easier to debug than plain `pr_info()` messages that contain no positional information.

---

## Private Data: Keeping Driver State

The probe function receives one device, but a driver must be able to handle multiple instances — if you plug in two TMP102 sensors, both will call the same `probe` function with different client pointers. The driver needs somewhere to store per-device state: which client pointer belongs to which device, whether it has a mutex initialised, any cached values, and so on.

The kernel pattern for this is a private data struct. You define a struct that holds all the state for one instance of your device, allocate one of these structs in `probe`, and attach it to the device. Other functions in the driver retrieve it by asking for the driver data attached to that device.

```c
/* Define all per-device state in one struct */
struct my_driver_data {
    struct i2c_client *client;
    struct mutex lock;
    int last_reading;
};

static int my_driver_probe(struct i2c_client *client, ...)
{
    struct my_driver_data *data;

    /* Allocate memory for this device's private data */
    data = devm_kzalloc(&client->dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    /* Fill in the fields */
    data->client = client;
    mutex_init(&data->lock);

    /* Store the pointer so other functions can find it later */
    i2c_set_clientdata(client, data);
    return 0;
}

/* In any other function, retrieve the private data like this: */
static void some_other_function(struct i2c_client *client)
{
    struct my_driver_data *data = i2c_get_clientdata(client);
    /* Now data points to the struct allocated in probe */
}
```

This pattern — allocate a private struct in `probe`, attach it to the device, retrieve it in other functions — is universal in Linux drivers. Every driver you ever read will use it in some form.

---

## `devm_` Memory Management: The RAII Pattern for Drivers

You may have noticed `devm_kzalloc` in the example above rather than the regular kernel allocator `kzalloc`. The `devm_` prefix stands for *device-managed*, and it is one of the most important modern kernel patterns to understand.

The problem it solves is cleanup. In a driver with several setup steps in `probe`, each step might need its own allocation or resource. If step 4 fails after steps 1 through 3 have already succeeded, you need to undo steps 1 through 3 in the correct reverse order before returning an error. As the number of setup steps grows, this cleanup code grows in complexity, becomes error-prone, and is historically a major source of resource leaks in kernel drivers.

The `devm_` functions solve this by binding allocations and resource registrations to the device's lifetime. When the device is removed — whether `remove` is called cleanly or `probe` returns an error partway through — the kernel automatically releases every `devm_`-allocated resource in reverse order, without you writing any cleanup code at all.

The difference is stark:

```c
/* Without devm_ — you must track and free everything yourself */
static int probe_without_devm(struct i2c_client *client, ...)
{
    char *buf1 = kmalloc(100, GFP_KERNEL);
    if (!buf1) return -ENOMEM;

    char *buf2 = kmalloc(200, GFP_KERNEL);
    if (!buf2) {
        kfree(buf1);   /* Must manually clean up buf1 */
        return -ENOMEM;
    }
    /* ... */
    return 0;
}

static void remove_without_devm(struct i2c_client *client)
{
    /* Must manually free everything allocated in probe */
    kfree(buf2);
    kfree(buf1);
}

/* With devm_ — the kernel handles all cleanup automatically */
static int probe_with_devm(struct i2c_client *client, ...)
{
    char *buf1 = devm_kzalloc(&client->dev, 100, GFP_KERNEL);
    if (!buf1) return -ENOMEM;

    char *buf2 = devm_kzalloc(&client->dev, 200, GFP_KERNEL);
    if (!buf2) return -ENOMEM;   /* buf1 freed automatically */
    /* ... */
    return 0;
}

/* remove can often be empty or even omitted when using devm_ */
static int remove_with_devm(struct i2c_client *client)
{
    return 0;   /* devm_ handles everything */
}
```

The `devm_` version is not just shorter — it is safer, because there are no manual cleanup paths to forget or get wrong. Modern kernel code uses `devm_` allocations wherever possible, and you will see them throughout the TMP102 driver.

---

## The Mutex: Protecting Shared State from Concurrent Access

The final concept to introduce in this document is the mutex, which the TMP102 driver uses around every hardware read. On a multi-core system like the Pi 4, multiple CPU cores can be running kernel code simultaneously. If two processes both try to read the temperature sensor at the same moment, they will both call `tmp102_read_temperature` concurrently.

In the temperature sensor case, the concern is specifically around the I2C transaction: reading a register over I2C involves sending a command byte and then reading back two data bytes as a single logical operation. If two concurrent callers both try to do this at the same time, their transactions could interleave on the bus and produce garbled data.

A mutex (mutual exclusion lock) prevents this by ensuring only one caller can be inside the protected region at a time. The pattern is always the same: lock before, unlock after.

```c
mutex_lock(&data->lock);    /* Block here if another caller holds the lock */
temp = read_the_sensor();   /* Only one caller reaches here at a time */
mutex_unlock(&data->lock);  /* Release the lock so others can proceed */
```

One important rule: a mutex acquired in kernel code must always be released, on every code path — including error paths. Forgetting to call `mutex_unlock` before returning an error leaves the mutex permanently locked, and the next caller trying to acquire it will block forever, hanging the entire read path.

---

## Putting the Model Together

You now understand the three foundational concepts of the Linux device model that the TMP102 driver relies on. Probe is where your driver sets things up and is called by the bus subsystem when hardware is matched, not by you directly. Private data is a per-device struct that holds all state, allocated in probe with `devm_kzalloc` and retrieved in other functions via `i2c_get_clientdata`. The mutex protects any operation that must not be interrupted by a concurrent caller on another CPU.

Every concept you have seen in this document will appear verbatim in the TMP102 driver. Before that driver can be discussed, though, there are two more concepts to establish: how the kernel knows a device exists (device trees, document 04) and how the I2C protocol works and what the kernel's I2C API looks like (document 05).

**Next: [04 — Device Trees](04-device-trees.md)**
