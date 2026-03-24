# 07 — Building the TMP102 Driver

Every concept introduced in the previous six documents now converges here. This document walks through the complete TMP102 driver line by line, explaining how each piece connects to what you already know. By the end, none of the code should feel unfamiliar — you have seen every pattern before, just not assembled together in a single file.

---

## Before You Start: Prerequisites Checklist

Make sure the following are in place before building the driver:

```bash
# Kernel headers installed
ls /lib/modules/$(uname -r)/build/include/linux/module.h

# I2C tools installed
which i2cdetect

# Device tree compiler installed
which dtc

# I2C enabled and sensor visible
sudo i2cdetect -y 1   # Should show 48 in the grid
```

If `i2cdetect` does not show `48`, stop here and re-check your wiring and
I2C configuration from document 05 before continuing.

---

## The Complete Driver

Create your working directory and source file:

```bash
mkdir -p ~/kernel-modules/tmp102
cd ~/kernel-modules/tmp102
nano tmp102.c
```

Here is the complete driver. Read the comments as you type it — they are part
of the teaching, not just decoration.

```c
/*
 * tmp102.c — Kernel driver for the Texas Instruments TMP102 I2C temperature sensor
 *
 * This driver reads the TMP102's temperature register over I2C and exposes
 * the reading as a sysfs attribute under /sys/class/hwmon/, making it
 * accessible to standard hardware monitoring tools like lm-sensors.
 *
 * Hardware: TMP102 at I2C address 0x48 (ADD0 tied to GND) on I2C bus 1.
 *
 * SPDX-License-Identifier: GPL-2.0
 */

/*
 * Each #include pulls in the declarations for a specific part of the kernel API.
 * You only need to include what you actually use — the kernel does not have a
 * "kitchen sink" header like <stdio.h> that covers everything.
 */
#include <linux/module.h>       /* module_init, module_exit, MODULE_* macros */
#include <linux/i2c.h>          /* i2c_client, i2c_smbus_read_word_swapped   */
#include <linux/hwmon.h>        /* devm_hwmon_device_register_with_groups    */
#include <linux/hwmon-sysfs.h>  /* SENSOR_DEVICE_ATTR, ATTRIBUTE_GROUPS      */
#include <linux/mutex.h>        /* mutex_init, mutex_lock, mutex_unlock       */
#include <linux/of.h>           /* of_device_id, MODULE_DEVICE_TABLE for DT  */

/* The TMP102 temperature register address. There are four registers
 * in total (0x00 through 0x03), but reading current temperature only
 * requires register 0x00. */
#define TMP102_TEMP_REG  0x00

/*
 * Private data struct: holds all per-device state for one TMP102 instance.
 *
 * Why a struct? Because a driver can manage multiple physical devices
 * simultaneously (e.g., two TMP102 sensors on different I2C addresses).
 * Each device gets its own instance of this struct, and the kernel stores
 * a pointer to it alongside the device. This is the pattern from doc 03.
 */
struct tmp102_data {
    struct i2c_client *client;  /* The I2C connection to this specific sensor */
    struct mutex lock;          /* Prevents concurrent accesses to the I2C bus */
};

/*
 * tmp102_read_temperature - Reads the raw register and converts to millidegrees C.
 *
 * The TMP102 temperature register layout (16 bits):
 *
 *   Bit:  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
 *         [D11 D10  D9  D8  D7  D6  D5  D4  D3  D2  D1  D0  --  --  --  --]
 *          ^--- 12-bit temperature data, MSB first ---^    ^-- unused --^
 *
 * The temperature is stored in the upper 12 bits (bits 15 down to 4).
 * The lower 4 bits are always zero and should be discarded.
 * Each unit of the 12-bit value represents 0.0625°C (1/16 of a degree).
 *
 * Conversion: shift raw right by 4 to extract the 12-bit value,
 *             then multiply by 1000 and divide by 16 to get millidegrees.
 *             (1000/16 = 62.5, i.e. 0.0625°C per count × 1000 = 62.5 millidegrees)
 *             Integer division by 16 avoids floating point in the kernel.
 *
 * Returns: temperature in millidegrees Celsius (positive or negative),
 *          or a negative error code if the I2C read failed.
 */
static long tmp102_read_temperature(struct i2c_client *client)
{
    s32 raw;
    s16 value;

    /*
     * i2c_smbus_read_word_swapped performs a standard SMBus word read:
     *   1. Sends the register address (TMP102_TEMP_REG = 0x00)
     *   2. Reads back 2 bytes
     *   3. Swaps the byte order (TMP102 sends big-endian; CPU is little-endian)
     *
     * Returns the 16-bit register value on success, or a negative error
     * code if anything went wrong on the I2C bus.
     */
    raw = i2c_smbus_read_word_swapped(client, TMP102_TEMP_REG);
    if (raw < 0)
        return raw;   /* Propagate the error — caller must check for < 0 */

    /*
     * Cast to s16 before shifting to preserve the sign bit.
     * For temperatures below 0°C, the raw value's MSB is 1 (negative in
     * two's complement). If we shifted an s32 right by 4, we'd get the
     * wrong result because the upper 16 bits would be zeros. By casting
     * to s16 first, we keep the correct 16-bit signed representation,
     * and the arithmetic right shift then sign-extends correctly.
     */
    value = (s16)raw >> 4;

    /* Multiply by 1000 to convert to millidegrees, divide by 16 for the
     * 0.0625°C per count scale factor. Example: 23.125°C raw = 370 counts,
     * 370 * 1000 / 16 = 23125 millidegrees. */
    return (value * 1000) / 16;
}

/*
 * temp_show - sysfs read callback for the temp1_input attribute.
 *
 * The kernel calls this function every time user space reads
 * /sys/class/hwmon/hwmonN/temp1_input. This function is the bridge
 * between a filesystem read and a hardware register read.
 *
 * Parameters:
 *   dev  - the device struct associated with this hwmon device
 *   attr - the specific attribute being read (unused here, but required by API)
 *   buf  - a kernel-provided buffer; write the result here as a string.
 *          The kernel forwards whatever we write here to the reader.
 *
 * Returns: number of bytes written to buf on success, negative error code on failure.
 */
static ssize_t temp_show(struct device *dev,
                         struct device_attribute *attr,
                         char *buf)
{
    /*
     * dev_get_drvdata retrieves the pointer we stored with i2c_set_clientdata
     * in probe. This is how non-probe functions reach the per-device state.
     */
    struct tmp102_data *data = dev_get_drvdata(dev);
    long temp;

    /*
     * Protect the I2C read with the mutex. If two processes both read
     * temp1_input simultaneously (e.g. two terminals running `cat` at
     * the same instant), only one will enter this block at a time.
     * The other will block at mutex_lock until the first completes.
     */
    mutex_lock(&data->lock);
    temp = tmp102_read_temperature(data->client);
    mutex_unlock(&data->lock);

    /* If the read failed, propagate the error to the caller. */
    if (temp < 0)
        return temp;

    /*
     * sprintf writes the temperature as a decimal string into buf.
     * The trailing newline is conventional for sysfs attributes —
     * shell tools like cat expect it.
     * Returns the number of bytes written, which is what sysfs needs.
     */
    return sprintf(buf, "%ld\n", temp);
}

/*
 * Define a sysfs attribute named "temp1_input" backed by temp_show.
 *
 * SENSOR_DEVICE_ATTR(name, permissions, show_fn, store_fn, index)
 *   name:        "temp1_input" — the filename in /sys/class/hwmon/hwmonN/
 *   permissions: 0444 — read by owner, group, and world; no writes
 *   show_fn:     temp_show — called on read
 *   store_fn:    NULL — writes are not allowed
 *   index:       0 — unused here, but useful when multiple attrs share one fn
 *
 * This macro generates a variable named sensor_dev_attr_temp1_input.
 */
static SENSOR_DEVICE_ATTR(temp1_input, 0444, temp_show, NULL, 0);

/*
 * Collect all attributes into a NULL-terminated array, then use
 * ATTRIBUTE_GROUPS to wrap it into the structure devm_hwmon_device_register_
 * with_groups expects.
 *
 * ATTRIBUTE_GROUPS(tmp102) generates:
 *   - struct attribute_group  tmp102_group  (singular)
 *   - const struct attribute_group *tmp102_groups[] (plural, NULL-terminated)
 *
 * We pass tmp102_groups (plural) to the registration function.
 */
static struct attribute *tmp102_attrs[] = {
    &sensor_dev_attr_temp1_input.dev_attr.attr,
    NULL
};
ATTRIBUTE_GROUPS(tmp102);

/*
 * probe - Called by the I2C bus subsystem when the kernel matches this driver
 *         to the "ti,tmp102" device tree node.
 *
 * This is the real entry point of the driver. Everything that needs to
 * be set up — memory, hardware verification, subsystem registration — happens
 * here. The module_init function (generated by module_i2c_driver at the
 * bottom) only registers the driver struct; probe does the actual work.
 *
 * Parameters:
 *   client - the i2c_client struct representing our specific sensor instance.
 *            Contains the I2C address, the bus number, and a pointer to the
 *            bus adapter driver.
 *   id     - which entry in the id_table matched this device (unused here).
 *
 * Returns: 0 on success, negative error code on failure.
 *          A non-zero return tells the kernel to abort loading the driver
 *          for this device.
 */
static int tmp102_probe(struct i2c_client *client,
                        const struct i2c_device_id *id)
{
    struct device *dev = &client->dev;  /* Convenience alias used throughout */
    struct tmp102_data *data;
    long initial_temp;

    /*
     * Allocate zeroed memory for this device's private data.
     *
     * devm_kzalloc: device-managed, zeroing kmalloc.
     *   dev:         bind this allocation to the device lifetime
     *   sizeof(*data): allocate exactly enough for one tmp102_data struct
     *   GFP_KERNEL:  normal allocation; may sleep if memory is tight
     *                (GFP_ATOMIC would be needed in interrupt context,
     *                 but probe runs in process context so GFP_KERNEL is fine)
     *
     * Returns NULL if allocation fails. The null check and -ENOMEM return
     * are mandatory — this is never omitted in production kernel code.
     */
    data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    /* Store the client pointer so temperature-reading functions can use it */
    data->client = client;

    /* Initialise the mutex before anyone tries to acquire it */
    mutex_init(&data->lock);

    /*
     * Attach our private data to the i2c_client so other functions can
     * retrieve it. The i2c_client is the "anchor" that persists through
     * all callbacks — private data is always retrieved through it.
     */
    i2c_set_clientdata(client, data);

    /*
     * Take a test reading before committing to registration.
     * This verifies the sensor is physically present and responding
     * before we claim everything is working.
     * If the sensor is not wired correctly, we fail here with a clear
     * message rather than registering a device that cannot produce data.
     */
    initial_temp = tmp102_read_temperature(client);
    if (initial_temp < 0) {
        dev_err(dev, "Could not read from TMP102 — check your wiring\n");
        return initial_temp;
    }

    /*
     * dev_info uses dev to prefix the message with the device location,
     * so dmesg will show: "tmp102 1-0048: TMP102 found! Initial temperature: 23.125°C"
     * The abs() on the modulus handles negative temperatures correctly
     * so -5.500°C prints as "-5.500" not "-5.-500".
     */
    dev_info(dev, "TMP102 found! Initial temperature: %ld.%03ld°C\n",
             initial_temp / 1000, abs(initial_temp % 1000));

    /*
     * Register with the hwmon subsystem. This:
     *   - Assigns a hwmonN number to this device
     *   - Creates /sys/class/hwmon/hwmonN/
     *   - Creates temp1_input inside that directory
     *   - Links temp_show as the read handler for temp1_input
     *
     * All of this is automatically undone by devm_ when the device is removed.
     * The "tmp102" string becomes the value of the 'name' sysfs file,
     * which lm-sensors uses to identify the device type.
     */
    devm_hwmon_device_register_with_groups(dev, "tmp102", data, tmp102_groups);

    return 0;   /* 0 = probe succeeded, driver is active for this device */
}

/*
 * remove - Called when the device is removed or the module is unloaded.
 *
 * Because every resource in probe was allocated with devm_, there is
 * nothing to manually clean up here. The kernel's devm infrastructure
 * releases everything in reverse order automatically.
 *
 * In drivers with non-devm resources (hardware that needs explicit power-down,
 * interrupts that must be unregistered, etc.), this function would be
 * more substantial. For this driver, a log message is sufficient.
 */
static int tmp102_remove(struct i2c_client *client)
{
    dev_info(&client->dev, "TMP102 driver removed\n");
    return 0;
}

/*
 * Device matching tables.
 *
 * Two tables are provided for two matching mechanisms:
 *   of_match_table: matches against device tree compatible strings
 *   id_table:       matches against strings from older platform registration
 *
 * Modern Raspberry Pi drivers primarily rely on of_match_table,
 * but including id_table provides compatibility with older kernel infrastructure.
 *
 * MODULE_DEVICE_TABLE makes these tables visible to the module loading
 * tools (depmod, modprobe), so the OS knows which devices each module supports
 * and can auto-load the correct module when a matching device appears.
 */
static const struct of_device_id tmp102_of_match[] = {
    { .compatible = "ti,tmp102" },  /* Must exactly match the DTS compatible string */
    { }                              /* Empty entry terminates the table */
};
MODULE_DEVICE_TABLE(of, tmp102_of_match);

static const struct i2c_device_id tmp102_id[] = {
    { "tmp102", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, tmp102_id);

/*
 * The i2c_driver struct describes this driver to the I2C bus subsystem.
 * The bus subsystem uses this struct to:
 *   - Know which compatible strings to match against (.of_match_table)
 *   - Know which function to call when a match is found (.probe)
 *   - Know which function to call on device removal (.remove)
 */
static struct i2c_driver tmp102_driver = {
    .driver = {
        .name           = "tmp102",
        .of_match_table = tmp102_of_match,
        .owner          = THIS_MODULE,  /* Prevents unloading while devices use it */
    },
    .probe     = tmp102_probe,
    .remove    = tmp102_remove,
    .id_table  = tmp102_id,
};

/*
 * module_i2c_driver is a convenience macro that generates the module_init
 * and module_exit functions automatically. Those generated functions call
 * i2c_add_driver (to register tmp102_driver with the I2C bus subsystem) on
 * load, and i2c_del_driver (to unregister it) on unload.
 *
 * This replaces the need to write init/exit functions manually for
 * drivers that only register a single driver struct on init and
 * unregister it on exit.
 */
module_i2c_driver(tmp102_driver);

MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("TI TMP102 I2C temperature sensor driver");
MODULE_LICENSE("GPL");
```

---

## Building, Installing, and Testing

Create the Makefile:

```bash
nano Makefile
```

```makefile
obj-m += tmp102.o
KDIR  := /lib/modules/$(shell uname -r)/build
PWD   := $(shell pwd)
all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
```

Build the driver and compile the device tree overlay:

```bash
# Build the kernel module
make

# The overlay file is in examples/03_tmp102_driver/ of this repo,
# or create tmp102-overlay.dts from doc 04 and compile it:
dtc -@ -I dts -O dtb -o tmp102-overlay.dtbo tmp102-overlay.dts
sudo cp tmp102-overlay.dtbo /boot/overlays/

# Add the overlay to boot config (only once — check it is not already there)
grep -q "tmp102-overlay" /boot/firmware/config.txt || \
    echo "dtoverlay=tmp102-overlay" | sudo tee -a /boot/firmware/config.txt

sudo reboot
```

After the reboot, load the driver and verify everything works:

```bash
# Load the driver
sudo insmod ~/kernel-modules/tmp102/tmp102.ko

# Check the kernel log — you should see the "TMP102 found!" message
dmesg | grep tmp102

# Find which hwmon number was assigned (may be hwmon0, hwmon1, etc.)
cat /sys/class/hwmon/hwmon*/name

# Read the temperature (adjust the hwmonN number to match what you found above)
cat /sys/class/hwmon/hwmon1/temp1_input
```

The number you see — something like `23125` — is your room temperature in millidegrees Celsius. 23125 means 23.125°C.

To confirm the driver is genuinely reading the sensor rather than returning a static value, hold the sensor chip gently between your fingers for about ten seconds. Body temperature is around 37°C — the reading should climb noticeably. Release it and the value will drift back down toward room temperature over the next minute.

If `lm-sensors` is installed, your TMP102 will appear automatically:

```bash
sudo apt install lm-sensors
sensors
```

To unload the driver when done:

```bash
sudo rmmod tmp102
```

---

## What You Have Built

The driver you just wrote is a real, production-pattern Linux kernel driver. It implements the probe model correctly, uses `devm_` memory management throughout, protects hardware access with a mutex, integrates with the hwmon subsystem using standardised attribute names, and works with tools that know nothing about the TMP102 specifically. Every pattern in it appears in drivers throughout the Linux kernel source tree.

The natural next steps from here are adding the TMP102's alert threshold registers (which would add `temp1_min` and `temp1_max` attributes), implementing one-shot mode to save power by putting the sensor to sleep between readings, or applying the same patterns to a different I2C sensor — nearly all of them follow the identical structure you have just learned.

**Next: [08 — Troubleshooting](08-troubleshooting.md)**
