/*
 * tmp102.c — Linux kernel driver for the TI TMP102 I2C temperature sensor.
 *
 * This is the complete, final driver from docs/07-tmp102-driver.md.
 * It combines everything introduced across the tutorial documents:
 *
 *   docs/02  — module structure, __init/__exit, pr_info / dmesg
 *   docs/03  — probe/remove pattern, private data, devm_, mutex
 *   docs/04  — device tree compatible string matching
 *   docs/05  — i2c_smbus_read_word_swapped, i2c_client
 *   docs/06  — SENSOR_DEVICE_ATTR, ATTRIBUTE_GROUPS, hwmon registration
 *
 * When loaded with the device tree overlay active, this driver:
 *   1. Is matched to the TMP102 by the "ti,tmp102" compatible string
 *   2. Calls probe, which reads the sensor and registers with hwmon
 *   3. Creates /sys/class/hwmon/hwmonN/temp1_input
 *   4. Returns the live temperature in millidegrees Celsius on every read
 *
 * Build:
 *   make
 *
 * Deploy:
 *   dtc -@ -I dts -O dtb -o tmp102-overlay.dtbo tmp102-overlay.dts
 *   sudo cp tmp102-overlay.dtbo /boot/overlays/
 *   echo "dtoverlay=tmp102-overlay" | sudo tee -a /boot/firmware/config.txt
 *   sudo reboot
 *
 * Test:
 *   sudo insmod tmp102.ko
 *   dmesg | grep tmp102
 *   cat /sys/class/hwmon/hwmon*/temp1_input
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/hwmon.h>
#include <linux/hwmon-sysfs.h>
#include <linux/mutex.h>
#include <linux/of.h>

#define TMP102_TEMP_REG  0x00

/* All per-device state lives in this struct. One instance is allocated
 * per physical TMP102 sensor. See docs/03-device-model.md. */
struct tmp102_data {
    struct i2c_client *client;
    struct mutex lock;
};

/*
 * Read the temperature register and convert the raw value to millidegrees C.
 *
 * TMP102 register format (16 bits, big-endian from sensor):
 *   bits [15:4] — 12-bit two's complement temperature, 0.0625°C per count
 *   bits [3:0]  — unused, always zero
 *
 * After byte-swap by i2c_smbus_read_word_swapped:
 *   Cast raw to s16 to preserve the sign bit (important for sub-zero temps)
 *   Shift right 4 to extract the 12-bit value
 *   Multiply by 1000 / 16 to convert to millidegrees (no floating point)
 *
 * Returns millidegrees Celsius, or a negative error code on I2C failure.
 */
static long tmp102_read_temperature(struct i2c_client *client)
{
    s32 raw;
    s16 value;

    raw = i2c_smbus_read_word_swapped(client, TMP102_TEMP_REG);
    if (raw < 0)
        return raw;

    value = (s16)raw >> 4;
    return (value * 1000) / 16;
}

/*
 * temp_show — sysfs read callback for /sys/class/hwmon/hwmonN/temp1_input.
 *
 * Called by the kernel every time user space reads the temp1_input file.
 * The mutex ensures this is safe even if two processes read simultaneously.
 * sprintf writes the temperature string into buf; the kernel returns buf
 * to the reading process.
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
        return temp;

    return sprintf(buf, "%ld\n", temp);
}

/* Bind the temp_show function to a sysfs file named "temp1_input".
 * 0444 = readable by all, writable by none. NULL store_fn = no writes. */
static SENSOR_DEVICE_ATTR(temp1_input, 0444, temp_show, NULL, 0);

/* Collect the attribute into a group. ATTRIBUTE_GROUPS(tmp102) generates
 * tmp102_groups (plural), which is passed to the registration function. */
static struct attribute *tmp102_attrs[] = {
    &sensor_dev_attr_temp1_input.dev_attr.attr,
    NULL
};
ATTRIBUTE_GROUPS(tmp102);

/*
 * probe — the real entry point of the driver.
 *
 * Called by the I2C bus subsystem when it matches "ti,tmp102" in the
 * device tree against our of_match_table. Sets up private data, verifies
 * the hardware responds, and registers with the hwmon subsystem.
 *
 * All allocations use devm_ so cleanup on error or removal is automatic.
 */
static int tmp102_probe(struct i2c_client *client,
                        const struct i2c_device_id *id)
{
    struct device *dev = &client->dev;
    struct tmp102_data *data;
    long initial_temp;

    data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    data->client = client;
    mutex_init(&data->lock);
    i2c_set_clientdata(client, data);

    /* Verify the sensor is physically present before claiming success */
    initial_temp = tmp102_read_temperature(client);
    if (initial_temp < 0) {
        dev_err(dev, "Could not read from TMP102 — check your wiring\n");
        return initial_temp;
    }

    /* abs() on the fractional part handles -5.500°C → "-5.500" correctly */
    dev_info(dev, "TMP102 found! Initial temperature: %ld.%03ld°C\n",
             initial_temp / 1000, abs(initial_temp % 1000));

    /* Register with hwmon: creates /sys/class/hwmon/hwmonN/ and all
     * attributes in tmp102_groups. Automatically undone on remove. */
    devm_hwmon_device_register_with_groups(dev, "tmp102", data, tmp102_groups);

    return 0;
}

static int tmp102_remove(struct i2c_client *client)
{
    dev_info(&client->dev, "TMP102 driver removed\n");
    return 0;
    /* devm_ handles all resource cleanup automatically */
}

static const struct of_device_id tmp102_of_match[] = {
    { .compatible = "ti,tmp102" },
    { }
};
MODULE_DEVICE_TABLE(of, tmp102_of_match);

static const struct i2c_device_id tmp102_id[] = {
    { "tmp102", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, tmp102_id);

static struct i2c_driver tmp102_driver = {
    .driver = {
        .name           = "tmp102",
        .of_match_table = tmp102_of_match,
        .owner          = THIS_MODULE,
    },
    .probe     = tmp102_probe,
    .remove    = tmp102_remove,
    .id_table  = tmp102_id,
};

module_i2c_driver(tmp102_driver);

MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("TI TMP102 I2C temperature sensor driver");
MODULE_LICENSE("GPL");
