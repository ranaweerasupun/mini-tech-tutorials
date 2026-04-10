<!-- © 2025 [Supun Akalanka Sriyananda] — CC BY-NC 4.0. Free to share with attribution, not for commercial use. -->

# 01 — The Linux Kernel and Kernel Modules

Before touching any driver code, it's worth getting the mental model straight — where your code actually lives, and why kernel C plays by completely different rules than the C you've written before. None of this is specific to I2C or temperature sensors yet. It's the foundation. Get this right and everything that follows will make sense; skip it and you'll be copy-pasting things you don't understand.

---

## What the Kernel Actually Is

When your Raspberry Pi boots, the Linux kernel is the first substantial program that runs. It starts before your shell, before any application, before anything you'd recognise as a normal program. Its job is to be the one piece of software that knows how to talk directly to the hardware — the CPU, the memory controller, storage, network adapters, GPIO pins — and to provide a controlled, safe interface to all of that for everything running above it.

Think of the kernel as the manager of a shared building. The building's resources — meeting rooms, the kitchen, the printer — are like hardware: the CPU, memory, storage. The tenants are user programs: your Python script, your web browser, the SSH server. The tenants need resources to do their work, but they can't just walk into the server room and start reconfiguring things. The manager (the kernel) handles all resource requests, enforces rules about who gets what and when, and makes sure one tenant can't accidentally — or deliberately — wreck another tenant's environment.

This separation is enforced in hardware. Modern CPUs have privilege levels, usually called rings, with ring 0 being the most privileged and ring 3 being the least. The kernel runs in ring 0, where it has unrestricted access to all hardware instructions and all memory addresses. User programs run in ring 3, where certain instructions are forbidden and all memory accesses are mediated by the kernel. This boundary isn't just a convention — the CPU itself enforces it. If a user program tries to directly access hardware, the CPU generates a fault and the kernel terminates the offending process.

This is why kernel programming is a different discipline from application programming. Your driver code runs in ring 0. A bug in your driver doesn't crash just your program — it can corrupt kernel memory, hang the entire system, or silently corrupt data. The stakes are genuinely higher, which is why the kernel has its own conventions, its own memory management patterns, and its own rules that look strange until you understand why they exist.

---

## User Space and Kernel Space

The two privilege levels have names you'll see constantly: **kernel space** (ring 0, where the kernel and drivers run) and **user space** (ring 3, where all ordinary programs run).

The interface between them is the **system call** — a controlled entry point into the kernel. When your Python script calls `open()` to open a file, that function eventually invokes a system call that crosses the boundary into kernel space, asks the kernel to open the file, and returns the result back to user space. The crossing is expensive relative to a normal function call, which is why batching work and minimising system calls matters for performance.

As a driver writer, you won't be calling system calls — you'll be *implementing* the lower half of that stack. When a user program opens `/sys/class/hwmon/hwmon1/temp1_input` and reads from it, your driver's `temp_show` function runs in kernel space to produce the data that gets handed back. You never see the system call mechanism directly, but understanding that your code is on the kernel side of that boundary explains many of the rules you're about to learn.

---

## What a Kernel Module Is

Technically, everything in the kernel could be compiled into a single monolithic binary. Early Linux was closer to this model. The problem is that modern hardware is incredibly diverse — the kernel would need to contain drivers for every network card, every USB device, every temperature sensor ever made, resulting in an enormous binary where most of it is irrelevant to any particular machine.

The solution is the **kernel module** — a piece of kernel code compiled as a separate `.ko` (kernel object) file that can be loaded into the running kernel and unloaded again when it's no longer needed. When you load a module, its code is injected directly into kernel space and becomes part of the running kernel for as long as it stays loaded. When you unload it, that code is removed.

Crucially, a loaded module is not a separate process. It doesn't have its own stack or its own memory address space the way a process does. It is literally part of the kernel — the same address space, the same privilege level, access to all the same internal kernel functions. This is what gives it the power to do things no user program can do: configure hardware, register with kernel subsystems, intercept I/O operations. It's also what makes bugs so consequential.

The module lifecycle has two mandatory functions: an **init function** that runs when the module is loaded, and an **exit function** that runs when it is unloaded. These are the module's entry and exit points into kernel space. Everything your driver does — registering with subsystems, allocating resources, setting up hardware — starts from init. Everything that needs to be cleaned up before unloading happens in exit.

---

## How Kernel Code Differs From Application Code

If you've written C before, some things about kernel code will look familiar and some will seem strange. Understanding the differences upfront saves a lot of confusion later.

**No standard library.** Kernel code cannot use `<stdio.h>`, `<stdlib.h>`, `malloc()`, `printf()`, `exit()`, or any other function from the C standard library. Those functions ultimately depend on system calls and the C runtime, which assume a user-space context. In kernel space, you use the kernel's own equivalents: `kmalloc()` for memory allocation (and its safer `devm_` variants, which you'll meet in document 03), `printk()` for logging, and so on. The kernel headers in `/lib/modules/$(uname -r)/build/include/linux/` provide all of this.

**`printk()` instead of `printf()`.** The kernel's logging function is `printk()`. It works like `printf()` but prefixes each message with a log level: `KERN_INFO` for informational messages, `KERN_WARNING` for warnings, `KERN_ERR` for errors. Messages go to the kernel ring buffer and are read with `dmesg`. Modern kernel code uses helper macros like `pr_info()`, `pr_warn()`, `pr_err()`, and the device-aware `dev_info()`, `dev_err()` — thin wrappers around `printk()` that add context automatically.

**No floating point.** The kernel doesn't save and restore the CPU's floating-point registers on context switches (doing so on every context switch would be prohibitively expensive). As a result, kernel code must not use floating-point arithmetic. Temperature sensors typically return values in millidegrees Celsius to work around this: instead of `23.125`, the kernel works with `23125`. All arithmetic stays in integers.

**Memory allocation can fail, and must be checked.** In user space, `malloc()` almost never returns NULL in practice — the OS will kill other processes to free memory before letting an allocation fail. In kernel space, allocations can and do fail, especially when memory is fragmented or the system is under pressure. Every allocation must be followed by a null check, and returning `-ENOMEM` if allocation fails is mandatory, not optional.

**Error codes are negative integers.** The kernel convention for signalling errors is to return a negative integer, where the magnitude is a constant from `<linux/errno.h>`: `-ENOMEM` for out-of-memory, `-EINVAL` for an invalid argument, `-ENODEV` for device not found, and so on. A return value of 0 always means success. Many kernel functions return these codes, and checking for negative return values is as fundamental as checking for null pointers.

---

## The Module License Requirement

Every kernel module must declare a license with `MODULE_LICENSE()`. This isn't just a formality. The Linux kernel is released under the GPL (General Public License), and the kernel enforces a distinction between modules licensed under GPL-compatible terms and those that are not. When you load a module with `MODULE_LICENSE("GPL")`, the kernel grants it access to a wider set of internal symbols that are explicitly reserved for GPL-compatible code. Non-GPL modules get a more restricted API.

For learning purposes and for any driver you share publicly, `MODULE_LICENSE("GPL")` is the correct and expected choice. Loading a non-GPL module also marks the kernel as "tainted" — which matters if you ever file a kernel bug report, since a tainted kernel report may be dismissed as potentially caused by the proprietary module.

---

## What Comes Next

You now have the mental model that makes kernel driver development make sense: kernel space and user space are genuinely different environments with different rules, modules are live code inside the running kernel, and the conventions that look strange — no stdlib, no float, negative error codes — each exist for a specific technical reason.

In the next document, you'll write the simplest possible kernel module: one that does nothing except print a message when loaded and when unloaded. That minimal exercise will make the toolchain, the build process, and the load/unload cycle feel concrete before any driver complexity is added on top.

**Next: [02 — Your First Kernel Module](02-hello-module.md)**
