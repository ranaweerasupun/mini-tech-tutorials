<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 02 — Your First Kernel Module

The best way to make kernel development feel real rather than abstract is to write the simplest possible module, build it, load it into a running kernel, and watch it work. That's what this document does. The module itself is trivial — it prints a message when loaded and another when unloaded — but the process of building and running it is the foundation everything else is built on. Get this working and the rest becomes much less intimidating.

---

## Installing the Kernel Headers

Kernel modules are compiled against the headers of the running kernel — the internal C header files that define the data structures, macros, and function signatures your module will use. These headers must exactly match the kernel version running on your Pi, because the kernel's internal ABI (the layout of its internal structures) can change between versions.

Install them with:

```bash
sudo apt install raspberrypi-kernel-headers build-essential
```

After installation, there'll be a directory at `/lib/modules/$(uname -r)/build/` containing the headers and a partial build tree for your exact kernel version. This is what your Makefile will point at.

Verify the headers are present:

```bash
ls /lib/modules/$(uname -r)/build/include/linux/module.h
```

If that file exists, you're ready. If you get "No such file or directory", the headers package didn't install correctly — try `sudo apt install --reinstall raspberrypi-kernel-headers`.

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

Every line here reappears in the final driver, so it's worth understanding each one before moving on.

The `#include <linux/module.h>` header is required for every kernel module without exception — it defines the fundamental types and macros (`MODULE_LICENSE`, `module_init`, `module_exit`) that make a `.c` file a kernel module. Notice the path: `linux/module.h`, not the standard library path you'd use in a regular C program. All kernel headers live under `linux/`.

The `pr_info()` function is one of the `pr_*` family of logging macros, thin wrappers around `printk()`. `pr_info()` logs at the `KERN_INFO` level — normal operational messages. `pr_err()` logs at `KERN_ERR`. `pr_warn()` at `KERN_WARNING`. These messages go to the kernel ring buffer, not to your terminal. You read them with `dmesg`.

The `return 0` from `hello_init` is critical. If the init function returns anything other than 0, `insmod` treats the load as failed and reports an error. In the final driver, the init function (called `probe`) returns various negative error codes to signal different types of failures — but `return 0` always means success.

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

One thing to watch out for: the indented lines in a Makefile **must** use a tab character, not spaces. Many text editors silently convert tabs to spaces, which causes a confusing "missing separator" error. If you use `nano`, tabs are preserved correctly by default.

---

## Building the Module

Build it with:

```bash
make
```

You should see several lines of compiler output, ending with something like:

```
  LD [M]  /home/pi/kernel-modules/hello/hello.ko
```

The `hello.ko` file is your compiled kernel module. A few other files also get generated (`hello.mod.c`, `hello.mod.o`, `Module.symvers`, `modules.order`) — these are artefacts of the build process that the kernel build system uses to track module dependencies and symbol exports. You can ignore them for now.

Before loading, you can inspect some metadata about the built module:

```bash
modinfo hello.ko
```

This prints the license, author, description, and the kernel version the module was built for. That last field — "vermagic" — is checked by the running kernel when you try to load the module. If it doesn't match the currently running kernel exactly, the load is rejected. This is one of the more common stumbling blocks when the kernel gets updated without also updating the headers.

---

## Loading, Testing, and Unloading

Load the module into the running kernel:

```bash
sudo insmod hello.ko
```

`insmod` (insert module) injects your `.ko` file into kernel space and calls `hello_init`. The terminal returns to your prompt with no output — kernel log messages don't appear on the terminal by default. To see them:

```bash
dmesg | tail -5
```

You should see something like:

```
[12345.678901] Hello from kernel space!
```

The number in brackets is the timestamp in seconds since boot. That message came from your `pr_info()` call inside `hello_init`.

Confirm the module is loaded:

```bash
lsmod | grep hello
```

`lsmod` lists all currently loaded kernel modules. You should see `hello` with a use count of 0, meaning nothing else is currently depending on it.

Now unload it:

```bash
sudo rmmod hello
```

`rmmod` calls `hello_exit` and then removes the module's code from kernel space. Check the log again:

```bash
dmesg | tail -5
```

The goodbye message should be there now.

There's something worth pausing on here: your C code just ran inside the Linux kernel. It used a kernel logging function. It was injected into and removed from a running production kernel without a reboot. The system stayed completely stable throughout. That's the normal, expected behaviour — but when your later drivers work correctly, the same thing will be happening with vastly more complex code talking to real hardware.

---

## When Things Go Wrong: `dmesg` Is Your Debugger

In user-space programs you'd reach for `gdb` when something goes wrong. In kernel development, `dmesg` is your primary diagnostic tool. Kernel modules can't be attached to a debugger the same way user programs can, so logging messages at key points and reading them with `dmesg` is how you understand what's actually happening inside the kernel.

A workflow you'll use constantly:

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

For the temperature sensor driver, when you load it you'll see a message like `TMP102 found! Initial temperature: 23.125°C` in `dmesg`. When something is wired incorrectly and the sensor isn't responding, you'll see `Could not read from TMP102 — check your wiring`. These messages are what connects your code to reality, and writing informative log messages is one of the habits that separates maintainable kernel code from code that's a nightmare to debug six months later.

**Next: [03 — The Linux Device Model](03-device-model.md)**
