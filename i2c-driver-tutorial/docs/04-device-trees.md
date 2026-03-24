# 04 — Device Trees

In the previous document you learned that the kernel's bus subsystem acts as a matchmaker between drivers and devices. But that raises an obvious question: how does the kernel know what devices exist in the first place? For a USB keyboard, the USB protocol includes device enumeration — the device announces itself to the host. For a chip sitting on a two-wire I2C bus, there is no such mechanism. The bus has no discovery protocol. The sensor does not announce its presence. The kernel needs to be *told* the hardware exists.

That is the problem device trees solve.

---

## What a Device Tree Is

A **device tree** is a data structure that describes the hardware layout of a computer to the operating system. It is written in a human-readable language called DTS (Device Tree Source), compiled into a binary DTB (Device Tree Blob), and loaded into memory by the bootloader before the kernel starts. When the kernel boots, one of its very first acts is to read the device tree and learn about the hardware it is running on.

Think of the device tree as a wiring diagram in text form. It describes which buses exist (I2C bus 1, SPI bus 0), what is connected to each bus (a temperature sensor at address 0x48), and what software should handle each device (compatible = "ti,tmp102"). The hardware description (the device tree) is deliberately kept separate from the software that drives it (the kernel module). This separation is what allows a single kernel binary to run on many different hardware configurations — the device tree changes for each board, but the kernel itself does not.

---

## The Compatible String: The Critical Link

Every node in a device tree that represents a piece of hardware has a `compatible` property. This is a string that identifies what kind of device it is. The value is conventionally written as `"vendor,model"` — for example, `"ti,tmp102"` for Texas Instruments' TMP102, or `"bosch,bmp280"` for Bosch's BMP280 pressure sensor.

This string is the link between the device tree and your driver. In your driver code, you define a table of compatible strings your driver supports:

```c
static const struct of_device_id tmp102_of_match[] = {
    { .compatible = "ti,tmp102" },
    { }   /* Empty entry marks the end of the table */
};
```

When the kernel reads the device tree and finds a node with `compatible = "ti,tmp102"`, it searches all registered drivers for one whose `of_match_table` contains that string. When it finds your driver, it calls your `probe` function. The compatible string is the handshake that makes this all work — getting it wrong is one of the most common reasons a driver's `probe` is never called.

---

## Overlays: Patching the Device Tree at Boot

The base device tree for a Raspberry Pi describes the Pi's own hardware — the CPU, the memory controller, the built-in peripherals. It knows nothing about accessories you have connected to the GPIO header, because those are specific to your project, not to the Pi itself.

A **device tree overlay** is a patch that is applied to the base device tree at boot time, adding or modifying nodes. Instead of editing the Pi's base device tree (which would need to be redone after every kernel update), you write a small overlay that describes just your sensor and instructs the bootloader to apply it. The bootloader merges it with the base tree before handing control to the kernel.

---

## Anatomy of an Overlay File

Here is the overlay for the TMP102 sensor, which you will also see in the examples directory. Reading each part of it with the context from this document should make every line clear:

```dts
/dts-v1/;   /* Identifies this as a device tree source file */
/plugin/;   /* Marks this as an overlay (a plugin), not a full device tree */

/ {
    /* This overlay is intended for Broadcom BCM2835-family SoCs (all Pi models) */
    compatible = "brcm,bcm2835";

    fragment@0 {
        /*
         * target = <&i2c1> means "modify the node labelled i2c1 in the
         * base device tree". On the Raspberry Pi, i2c1 is the I2C bus
         * exposed on the 40-pin header (pins 3 and 5). The &i2c1 syntax
         * is a phandle reference — a pointer to another node by its label.
         */
        target = <&i2c1>;

        __overlay__ {
            /* Ensure the I2C bus node is marked as active */
            status = "okay";

            /*
             * "tmp102@48" is the node name. The convention is
             * "device-type@address" where address is the I2C address
             * in hexadecimal. This is the node describing our sensor.
             */
            tmp102@48 {
                /*
                 * This string must exactly match the .compatible entry
                 * in our driver's of_device_id table. This is the string
                 * the kernel uses to find the right driver for this device.
                 */
                compatible = "ti,tmp102";

                /*
                 * reg specifies the device's address on its bus.
                 * For I2C devices, this is the 7-bit I2C address.
                 * 0x48 is the address of the TMP102 when ADD0 is tied to GND.
                 */
                reg = <0x48>;

                status = "okay";
            };
        };
    };
};
```

The structure to notice is that the sensor node (`tmp102@48`) is nested inside the I2C bus node (`i2c1`). This parent-child relationship tells the kernel that this sensor lives on this particular I2C bus — it is a child device of that bus. The kernel's I2C bus driver will see this child node, match its compatible string to your driver, and call your `probe` function with an `i2c_client` struct populated from the node's properties — including the I2C address from the `reg` field.

---

## Compiling and Installing the Overlay

The DTS source file is human-readable but the kernel needs the compiled binary DTB or DTBO format. The device tree compiler `dtc` handles this:

```bash
# Install the compiler if you do not have it
sudo apt install device-tree-compiler

# Compile the overlay
# -@ enables symbol generation (required for overlays that reference other nodes)
# -I dts means input is device tree source
# -O dtb means output binary format
# -o names the output file
dtc -@ -I dts -O dtb -o tmp102-overlay.dtbo tmp102-overlay.dts
```

Install it where the bootloader looks for overlays:

```bash
sudo cp tmp102-overlay.dtbo /boot/overlays/
```

Then tell the bootloader to apply it at boot by adding a line to the Pi's boot configuration:

```bash
echo "dtoverlay=tmp102-overlay" | sudo tee -a /boot/firmware/config.txt
```

After a reboot, the kernel will start up with your sensor already described in its device tree, ready to be matched against your driver the moment the module loads.

---

## Verifying the Overlay Was Applied

After rebooting, you can confirm the overlay was applied and the kernel sees your sensor:

```bash
# List I2C devices the kernel knows about on bus 1
ls /sys/bus/i2c/devices/
```

You should see an entry named `1-0048` — the kernel's notation for "I2C bus 1, address 0x48". This entry exists because the device tree told the kernel a device exists there. When you load your driver module, the kernel will find this device and call your `probe` function.

```bash
# Check the compatible string the kernel recorded from the overlay
cat /sys/bus/i2c/devices/1-0048/of_node/compatible
```

If this prints `ti,tmp102`, the overlay was applied correctly and the compatible string matches what your driver will register.

One common question at this point is: why does `/sys/bus/i2c/devices/1-0048` exist even before the driver is loaded? The answer is that the device node in the kernel's internal bus list is created from the device tree entry, independently of whether any driver claims it. The device exists in the kernel's view of the world. It is simply unmanaged — no driver is attached to it yet — until a matching driver is registered.

**Next: [05 — I2C Protocol and the Kernel I2C Subsystem](05-i2c.md)**
