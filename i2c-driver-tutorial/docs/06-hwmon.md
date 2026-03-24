# 06 — The hwmon Subsystem

You now understand how a driver is matched to a device, how it stores its state, how it communicates with hardware over I2C, and how device trees describe hardware to the kernel. The one remaining piece before the complete driver is the output side: once your driver has read a temperature value from the sensor, how does it make that value available to user-space programs?

The answer is the hwmon subsystem — and understanding it means understanding two related Linux concepts: sysfs and kernel attributes.

---

## sysfs: The Kernel's Window to User Space

Linux exposes kernel state to user space in many ways, but one of the most elegant is **sysfs** — a virtual filesystem mounted at `/sys/`. Unlike real filesystems, sysfs does not store anything on disk. Its files and directories exist only in memory and are generated on demand by the kernel. Every file in `/sys/` is backed by a kernel function: when you read a file, the kernel calls a function to produce the content; when you write to a file, the kernel calls a different function to process the value.

Browse `/sys/` on your Pi and you can explore the entire kernel's view of the system:

```bash
# See all PCI devices the kernel knows about
ls /sys/bus/pci/devices/

# See the CPU's current scaling frequency
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

# See all I2C devices currently known to the kernel
ls /sys/bus/i2c/devices/
```

Each of these is not a real file with stored contents — it is a live window into kernel data structures, produced by calling kernel functions every time you read them.

The directory `/sys/class/hwmon/` is part of this system. It contains one directory per hardware monitoring device registered with the hwmon subsystem. Each `hwmonN` directory contains files with names like `temp1_input`, `temp2_input`, `fan1_input`, `in0_input` — standardised names that hardware monitoring tools like `lm-sensors` know how to read and interpret.

---

## Kernel Attributes: Connecting Files to Functions

In kernel driver code, the connection between a sysfs file and a function is made through a **kernel attribute**. An attribute binds together three things: a file name (what the file is called in `/sys/`), a set of permissions (read-only, write-only, or read-write), and one or two callback functions (one to handle reads, one to handle writes).

The hwmon subsystem provides a convenient macro for defining sensor-specific attributes called `SENSOR_DEVICE_ATTR`. Here is how the TMP102 driver uses it:

```c
/*
 * The temp_show function will be called every time someone reads
 * the temp1_input file. It reads the sensor and writes the result
 * into `buf`, which the kernel then returns to the reader.
 */
static ssize_t temp_show(struct device *dev,
                         struct device_attribute *attr,
                         char *buf)
{
    struct tmp102_data *data = dev_get_drvdata(dev);
    long temp;

    mutex_lock(&data->lock);
    temp = tmp102_read_temperature(data->client);
    mutex_unlock(&data->lock);

    if (temp < 0)
        return temp;    /* Propagate the error code to the caller */

    /* sprintf into buf produces the string that the reader receives */
    return sprintf(buf, "%ld\n", temp);
}

/*
 * SENSOR_DEVICE_ATTR(name, permissions, show_fn, store_fn, index)
 *
 * name:         the file name that will appear in /sys/
 * permissions:  0444 = readable by everyone, writable by no one
 * show_fn:      function called on read (temp_show)
 * store_fn:     function called on write (NULL = no writes allowed)
 * index:        used to distinguish multiple attributes sharing one function
 */
static SENSOR_DEVICE_ATTR(temp1_input, 0444, temp_show, NULL, 0);
```

After this definition, `sensor_dev_attr_temp1_input` is a variable that encapsulates the attribute. The name `sensor_dev_attr_temp1_input` is generated automatically by the macro from the name you gave it (`temp1_input`).

---

## Attribute Groups: Bundling Attributes Together

A driver often exposes multiple attributes at once — a temperature sensor with an alert threshold might expose `temp1_input`, `temp1_min`, and `temp1_max`. Rather than registering each attribute individually, the kernel uses **attribute groups** to bundle related attributes together and register them all in one operation.

An attribute group is just a NULL-terminated array of attribute pointers, wrapped in a struct, wrapped in a macro:

```c
/* The array of attributes to expose */
static struct attribute *tmp102_attrs[] = {
    &sensor_dev_attr_temp1_input.dev_attr.attr,
    NULL   /* NULL terminator marks the end of the array */
};

/*
 * ATTRIBUTE_GROUPS(tmp102) generates two things:
 *   - a struct attribute_group called tmp102_group
 *   - a const struct attribute_group * array called tmp102_groups
 *     (note the plural) pointing to tmp102_group and terminated with NULL.
 *
 * We pass tmp102_groups to devm_hwmon_device_register_with_groups,
 * which registers all the attributes in the group at once.
 */
ATTRIBUTE_GROUPS(tmp102);
```

The naming convention here matters: `ATTRIBUTE_GROUPS(tmp102)` generates a variable called `tmp102_groups` (plural), which is what gets passed to the registration function. Getting the name slightly wrong — passing `tmp102_group` instead of `tmp102_groups` — is a common typo that produces a compiler error.

---

## Registering with hwmon: The One Registration Call

With the attributes defined and grouped, registering the entire hardware monitoring device requires a single function call in `probe`:

```c
devm_hwmon_device_register_with_groups(dev, "tmp102", data, tmp102_groups);
```

This call does several things at once. It registers the device with the hwmon subsystem, which assigns it a `hwmonN` number. It creates the `/sys/class/hwmon/hwmonN/` directory. It creates all the attribute files specified in `tmp102_groups` inside that directory — in our case, just `temp1_input`. And because it begins with `devm_`, it automatically undoes all of this when the device is removed, with no cleanup code needed in `remove`.

After this call returns successfully, a user program can run `cat /sys/class/hwmon/hwmon1/temp1_input` and the kernel will call your `temp_show` function, read the sensor, and return the temperature. The connection between a text file in the filesystem and a hardware register on a chip over a two-wire bus is complete.

---

## How `lm-sensors` Uses This

The reason it matters that your driver follows the hwmon conventions — using `temp1_input` rather than, say, a custom file name — is that standard tools like `lm-sensors` understand those conventions. When you run `sensors`, the `lm-sensors` tool scans `/sys/class/hwmon/`, finds every `hwmonN` directory, reads the `name` file to identify the device, and then reads all the `temp*_input`, `fan*_input`, `in*_input`, and similar files it finds. It knows what those names mean and formats them into a human-readable display.

Because your driver registers with hwmon correctly and uses the standardised `temp1_input` name, `sensors` will find and display your TMP102 reading automatically, without any special configuration. This is exactly the kind of interoperability benefit that comes from using kernel subsystems correctly rather than inventing your own interface.

---

## The Full Flow, End to End

It is worth pausing before the final document to trace the complete journey from a user typing `cat /sys/class/hwmon/hwmon1/temp1_input` to a temperature appearing on screen, because you now have all the pieces to understand every step:

The shell invokes `cat`, which calls `open()` and then `read()` as system calls. Those system calls enter kernel space. The virtual filesystem (VFS) layer routes the `read()` to the sysfs handler for that particular file. The sysfs handler identifies the attribute behind the file and calls your `temp_show` function. Inside `temp_show`, you acquire the mutex, call `tmp102_read_temperature`, and release the mutex. Inside `tmp102_read_temperature`, you call `i2c_smbus_read_word_swapped`, which tells the kernel's I2C bus driver to perform a register read transaction. The I2C bus driver operates the hardware I2C controller on the BCM2711 chip, which drives the SCL and SDA lines. The TMP102 on those lines responds with two bytes of temperature data. The data travels back up: raw bytes to `i2c_smbus_read_word_swapped`, converted to a millidegrees value in your function, formatted into a string by `sprintf`, returned through sysfs, returned from the `read()` system call, and printed on screen by `cat`.

Every layer you have studied in this tutorial is present in that journey. The next document assembles all the pieces into the complete, working driver.

**Next: [07 — Building the TMP102 Driver](07-tmp102-driver.md)**
