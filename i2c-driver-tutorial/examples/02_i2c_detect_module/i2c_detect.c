/*
 * i2c_detect.c — A kernel module that probes for a TMP102 on the I2C bus.
 *
 * This is the intermediate step between the hello module and the full
 * TMP102 driver. It demonstrates:
 *
 *   - The i2c_driver struct and registration pattern
 *   - How probe and remove are called by the bus subsystem
 *   - Private data allocation with devm_kzalloc
 *   - The dev_info / dev_err logging family
 *   - Performing a real I2C read to verify hardware presence
 *
 * It does NOT register with hwmon or expose any sysfs attributes —
 * that is the job of the final driver. The goal here is to make the
 * probe/remove lifecycle feel familiar before adding the output layer.
 *
 * Study this alongside docs/03-device-model.md and docs/05-i2c.md.
 *
 * Prerequisites:
 *   - I2C enabled (raspi-config → Interface Options → I2C)
 *   - TMP102 wired to I2C bus 1 at address 0x48
 *   - Device tree overlay installed (see docs/04-device-trees.md)
 *   - Overlay applied (dtoverlay=tmp102-overlay in /boot/firmware/config.txt)
 *
 * Build:  make
 * Load:   sudo insmod i2c_detect.ko
 * Check:  dmesg | grep i2c_detect
 * Unload: sudo rmmod i2c_detect
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/of.h>

/* Register 0x00 is the TMP102 temperature register.
 * We only read it here to confirm the sensor is responding — we do not
 * interpret the value yet. That conversion logic is in the final driver. */
#define TMP102_TEMP_REG  0x00

/*
 * Per-device private data.
 *
 * This struct holds all state for one instance of the device. Even though
 * this example only needs the client pointer, it is good practice to have
 * the struct from the beginning — adding fields later is easy, and the
 * pattern of "allocate struct in probe, retrieve in other functions" is
 * something to internalise early.
 */
struct i2c_detect_data {
    struct i2c_client *client;
};

/*
 * probe — called by the I2C bus subsystem when it finds a device whose
 * compatible string matches an entry in our of_match_table.
 *
 * At this point the kernel has already verified the device tree entry
 * and populated the i2c_client struct with the bus number and address.
 * Our job is to confirm the hardware works and set up our state.
 */
static int i2c_detect_probe(struct i2c_client *client,
                             const struct i2c_device_id *id)
{
    struct device *dev = &client->dev;
    struct i2c_detect_data *data;
    s32 raw;

    /*
     * dev_info prefixes the log message with the device's location,
     * producing output like: "i2c_detect 1-0048: probe called"
     * This is much more useful than pr_info("probe called") when you
     * have multiple devices or are debugging across reboots.
     */
    dev_info(dev, "probe called — device at bus %d, address 0x%02x\n",
             client->adapter->nr, client->addr);

    /* Allocate private data, bound to the device lifetime via devm_ */
    data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
    if (!data) {
        dev_err(dev, "Failed to allocate memory\n");
        return -ENOMEM;
    }

    data->client = client;

    /* Attach private data to the client so remove() can retrieve it */
    i2c_set_clientdata(client, data);

    /*
     * Perform a test read of register 0x00.
     * A negative return means the I2C transaction failed — the sensor
     * did not respond, which almost always means a wiring problem.
     * Failing here in probe prevents registering a non-functional device.
     */
    raw = i2c_smbus_read_word_swapped(client, TMP102_TEMP_REG);
    if (raw < 0) {
        dev_err(dev, "I2C read failed (error %d) — check wiring\n", raw);
        return raw;
    }

    /*
     * We got data back. At this stage we just confirm the sensor is alive.
     * The raw value is logged in hex so you can cross-check it with:
     *   sudo i2cget -y 1 0x48 0x00 w
     * (The values may differ slightly between reads as temperature changes.)
     */
    dev_info(dev, "TMP102 responded! Raw register 0x00 = 0x%04x\n",
             (unsigned int)(raw & 0xFFFF));
    dev_info(dev, "Driver fully loaded. Use 'sudo rmmod i2c_detect' to unload.\n");

    return 0;
}

/*
 * remove — called when the device is removed or the module is unloaded.
 *
 * All memory allocated with devm_ is freed automatically when this
 * function returns, so there is nothing to clean up manually here.
 */
static int i2c_detect_remove(struct i2c_client *client)
{
    dev_info(&client->dev, "remove called — driver detaching from device\n");
    return 0;
}

/* Device matching tables — see docs/04-device-trees.md for explanation */
static const struct of_device_id i2c_detect_of_match[] = {
    { .compatible = "ti,tmp102" },
    { }
};
MODULE_DEVICE_TABLE(of, i2c_detect_of_match);

static const struct i2c_device_id i2c_detect_id[] = {
    { "tmp102", 0 },
    { }
};
MODULE_DEVICE_TABLE(i2c, i2c_detect_id);

/*
 * The i2c_driver struct registers this module with the I2C bus subsystem.
 * On load, the bus subsystem checks all known I2C devices against
 * of_match_table and calls probe for any matches found.
 */
static struct i2c_driver i2c_detect_driver = {
    .driver = {
        .name           = "i2c_detect",
        .of_match_table = i2c_detect_of_match,
        .owner          = THIS_MODULE,
    },
    .probe    = i2c_detect_probe,
    .remove   = i2c_detect_remove,
    .id_table = i2c_detect_id,
};

/*
 * module_i2c_driver generates the module_init and module_exit functions.
 * On init: calls i2c_add_driver(&i2c_detect_driver)
 * On exit: calls i2c_del_driver(&i2c_detect_driver)
 */
module_i2c_driver(i2c_detect_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("I2C device detection module — learning the probe pattern");
