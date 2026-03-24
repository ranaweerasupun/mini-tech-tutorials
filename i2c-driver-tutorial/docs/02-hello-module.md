# 02 — Your First Kernel Module

The best way to make kernel development feel concrete rather than abstract is to write the simplest possible module, build it, load it into a running kernel, and watch it work. This document does exactly that. The module itself is trivial — it prints a message when loaded and another when unloaded — but the process of building and running it is the foundation everything else is built on.

---

## Installing the Kernel Headers

Kernel modules are compiled against the headers of the running kernel — the internal C header files that define the data structures, macros, and function signatures your module will use. These headers must exactly match the kernel version running on your Pi, because the kernel's internal ABI (the layout of its internal structures) can change between versions.

Install them with:

```bash
sudo apt install raspberrypi-kernel-headers build-essential
```

After installation, you will find a directory at `/lib/modules/$(uname -r)/build/` that contains the headers and a partial build tree for your exact kernel version. This is what your Makefile will point at.

Verify the headers are present:

```bash
ls /lib/modules/$(uname -r)/build/include/linux/module.h
```

If that file exists, you are ready. If you get "No such file or directory", the headers package did not install correctly — try `sudo apt install --reinstall raspberrypi-kernel-headers`.

---

## The Code

Create a working directory and the source file:

```bash
mkdir -p ~/kernel-modules/hello
cd ~/kernel-modules/hello
nano hello.c
```

Type in this code exactly:

```c
#include <linux/module.h>   /* Required for all kernel modules */
#include <linux/init.h>     /* Required for __init and __exit macros */
#include <linux/kernel.h>   /* Required for KERN_INFO and pr_info() */

/*
 * __init marks this function as initialization-only code.
 * The kernel can discard it from memory after the module loads,
 * since it will never be called again. This saves a small amount
 * of kernel memory.
 */
static int __init hello_init(void)
{
    pr_info("Hello from kernel space!\n");
    /*
     * Return 0 to signal success. Any non-zero return value here
     * means the module failed to load, and insmod will report an error.
     */
    return 0;
}

/*
 * __exit marks this function as cleanup-only code.
 * If the module is compiled into the kernel (rather than as a .ko),
 * this function is never needed and the compiler discards it.
 */
static void __exit hello_exit(void)
{
    pr_info("Goodbye from kernel space!\n");
}

/*
 * These two macros tell the kernel which functions to call
 * when the module is loaded and unloaded. They are mandatory.
 */
module_init(hello_init);
module_exit(hello_exit);

/* These metadata macros are not strictly required, but they
 * are considered good practice and some kernel checks warn
 * if they are absent. */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("A minimal kernel module for learning");
```

Every line of this code deserves a moment of attention because every pattern you see here reappears in the final driver.

The `#include <linux/module.h>` header is required for every kernel module without exception — it defines the fundamental types and macros (`MODULE_LICENSE`, `module_init`, `module_exit`) that make a `.c` file a kernel module. Notice the path: `linux/module.h`, not the standard library path you would use in a regular C program. All kernel headers live under `linux/`.

The `pr_info()` function is one of the `pr_*` family of logging macros, which are thin wrappers around `printk()`. `pr_info()` logs at the `KERN_INFO` level, which is informational — messages that describe normal operations. `pr_err()` logs at `KERN_ERR`, used for errors. `pr_warn()` logs at `KERN_WARNING`. These messages go to the kernel ring buffer, not to your terminal. You read them with `dmesg`.

The `return 0` from `hello_init` is critical. If the init function returns anything other than 0, `insmod` treats the load as failed and displays an error. In the final driver, the init function (called `probe`) returns various negative error codes to signal different types of failures — `return 0` always means "everything worked."

---

## The Makefile

Create the Makefile in the same directory:

```bash
nano Makefile
```

```makefile
# obj-m tells the build system to compile hello.c as a kernel module (.ko)
# rather than building it into the kernel itself (which obj-y would do).
obj-m += hello.o

# KDIR points to the kernel build tree for the currently running kernel.
# $(shell uname -r) expands to the kernel version string (e.g. 6.1.21-v8+).
KDIR := /lib/modules/$(shell uname -r)/build

# PWD is the current directory — where our source file lives.
PWD  := $(shell pwd)

all:
	# -C $(KDIR) tells make to change into the kernel build tree first.
	# M=$(PWD) tells the kernel build system to then look in our directory
	# for the module source. This is the standard out-of-tree module build pattern.
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
```

One thing to be aware of: the indented lines in a Makefile **must** use a tab character, not spaces. Many text editors silently convert tabs to spaces, which will cause a confusing "missing separator" error. If you use `nano`, tabs should be preserved correctly by default.

---

## Building the Module

Build it with:

```bash
make
```

You should see several lines of compiler output scrolling by, ending with something like:

```
  LD [M]  /home/pi/kernel-modules/hello/hello.ko
```

The `hello.ko` file is your compiled kernel module. A few other files are also generated (`hello.mod.c`, `hello.mod.o`, `Module.symvers`, `modules.order`) — these are artefacts of the build process that the kernel build system uses to track module dependencies and symbol exports. You can ignore them for now.

If the build fails with an error about missing headers, double-check that `raspberrypi-kernel-headers` installed correctly. If it fails with "missing separator", check that the Makefile lines are indented with tabs.

You can inspect some metadata about the built module before loading it:

```bash
modinfo hello.ko
```

This prints the license, author, description, and the kernel version the module was built for. The "vermagic" field shows the exact kernel version — the running kernel checks this field when you try to load the module, and will refuse to load it if the version does not match.

---

## Loading, Testing, and Unloading

Load the module into the running kernel:

```bash
sudo insmod hello.ko
```

`insmod` (insert module) injects your `.ko` file into kernel space and calls your `hello_init` function. The terminal returns to your prompt with no output — kernel log messages do not appear on the terminal by default. To see them, read the kernel ring buffer:

```bash
dmesg | tail -5
```

You should see something like:

```
[12345.678901] Hello from kernel space!
```

The number in brackets is the timestamp in seconds since boot. This message came from your `pr_info()` call inside `hello_init`.

Confirm the module is currently loaded:

```bash
lsmod | grep hello
```

`lsmod` lists all currently loaded kernel modules. You should see `hello` in the list with a use count of 0, meaning nothing else is currently depending on it.

Now unload it:

```bash
sudo rmmod hello
```

`rmmod` (remove module) calls your `hello_exit` function and then removes the module's code from kernel space. Check the log again:

```bash
dmesg | tail -5
```

You should now see the goodbye message as well.

There is a small but important thing to appreciate about what just happened: your C code ran inside the Linux kernel. It used a kernel logging function. It was injected into and removed from a running production kernel without a reboot. The system remained stable the whole time. That is the normal, expected behaviour — but it is worth pausing to notice it, because when your later drivers work correctly, the same thing will be happening with vastly more complex code talking to real hardware.

---

## When Things Go Wrong: `dmesg` Is Your Debugger

In user-space programs, you use a debugger like `gdb` when something goes wrong. In kernel development, `dmesg` is your primary diagnostic tool. Kernel modules cannot easily be attached to a debugger in the same way user programs can, so logging messages at key points in your code and reading them with `dmesg` is how you understand what is happening.

A workflow you will use constantly:

```bash
# Load the module
sudo insmod my_module.ko

# Check what happened
dmesg | tail -20

# Unload the module
sudo rmmod my_module

# Check the exit messages
dmesg | tail -5
```

For the temperature sensor driver, when you load it you will see a message like `TMP102 found! Initial temperature: 23.125°C` in `dmesg`. When something is wired incorrectly and the sensor is not responding, you will see `Could not read from TMP102 — check your wiring`. These messages are what connects your code to reality, and writing good, informative log messages is one of the habits that separates maintainable kernel code from code that is a nightmare to debug six months later.

**Next: [03 — The Linux Device Model](03-device-model.md)**
