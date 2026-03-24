# 01 — The Linux Kernel and Kernel Modules

Before you write a single line of driver code, you need a clear mental model
of where that code lives and why it is fundamentally different from ordinary
C programs. This document builds that model. Nothing here is specific to I2C
or temperature sensors — it is the conceptual foundation that makes everything
else make sense.

---

## What the Kernel Actually Is

When your Raspberry Pi boots, the Linux kernel is the first substantial program
that runs. It starts before your shell, before any application, before anything
you would recognise as a program. Its job is to be the one piece of software
that knows how to talk directly to the hardware — the CPU, the memory controller,
the storage, the network adapter, the GPIO pins — and to provide a controlled,
safe interface to all of that hardware for everything running above it.

Think of the kernel as the manager of a shared building. The building's
resources — meeting rooms, the kitchen, the printer — are like hardware: the
CPU, memory, storage. The tenants are user programs: your Python script, your
web browser, the SSH server. The tenants need resources to do their work, but
they cannot just walk into the server room and start reconfiguring things. The
manager (the kernel) handles all resource requests, enforces rules about who
gets what and when, and makes sure one tenant cannot accidentally — or
deliberately — mess up another tenant's environment.

This separation is enforced in hardware. Modern CPUs have privilege levels,
usually called rings, with ring 0 being the most privileged and ring 3 being
the least. The kernel runs in ring 0, where it has unrestricted access to
all hardware instructions and all memory addresses. User programs run in ring 3,
where certain instructions are forbidden and all memory accesses are mediated
by the kernel. This boundary is not just a convention — the CPU itself enforces
it. If a user program tries to directly access hardware, the CPU generates a
fault and the kernel terminates the offending program.

This is why kernel programming is a different discipline from application
programming. Your driver code runs in ring 0. A bug in your driver does not
crash just your program — it can corrupt kernel memory, hang the entire system,
or silently corrupt data. The stakes are genuinely higher, which is why the
kernel has its own conventions, its own memory management patterns, and its
own rules that look strange until you understand why they exist.

---

## User Space and Kernel Space

The two privilege levels have names you will see constantly: **kernel space**
(ring 0, where the kernel and drivers run) and **user space** (ring 3, where
all ordinary programs run).

The interface between them is the **system call** — a controlled entry point
into the kernel. When your Python script calls `open()` to open a file, that
function eventually invokes a system call that crosses the boundary into kernel
space, asks the kernel to open the file, and returns the result back to user
space. The crossing is expensive relative to a normal function call, which is
why batching work and minimising system calls matters for performance.

As a driver writer, you will not be calling system calls — you will be
*implementing* the lower half of that stack. When a user program opens
`/sys/class/hwmon/hwmon1/temp1_input` and reads from it, your driver's
`temp_show` function runs in kernel space to produce the data that gets
handed back. You never see the system call mechanism directly, but
understanding that your code is on the kernel side of that boundary explains
many of the rules you are about to learn.

---

## What a Kernel Module Is

Technically, everything in the kernel could be compiled into a single
monolithic binary. Early Linux was closer to this model. The problem is that
modern hardware is incredibly diverse — the kernel would need to contain
drivers for every network card, every USB device, every temperature sensor
ever made, resulting in an enormous binary, most of which is irrelevant to
any particular machine.

The solution is the **kernel module** — a piece of kernel code compiled as a
separate `.ko` (kernel object) file that can be loaded into the running kernel
and unloaded again when it is no longer needed. When you load a module, its
code is injected directly into kernel space and becomes part of the running
kernel for as long as it is loaded. When you unload it, that code is removed.

Crucially, a loaded module is not a separate process. It does not have its own
stack or its own memory address space in the way a process does. It is
literally part of the kernel — the same address space, the same privilege level,
access to all the same internal kernel functions. This is what gives it the
power to do things no user program can do: configure hardware, register with
kernel subsystems, and intercept I/O operations. It is also what makes bugs
so consequential.

The module lifecycle has two mandatory functions: an **init function** that
runs when the module is loaded, and an **exit function** that runs when it is
unloaded. These are the module's entry and exit points into kernel space.
Everything your driver does — registering with subsystems, allocating resources,
setting up hardware — starts from init. Everything that needs to be cleaned up
before unloading happens in exit.

---

## How Kernel Code Differs From Application Code

If you have written C before, some things about kernel code will look familiar
and some will seem strange. Understanding the differences upfront prevents
confusion later.

**No standard library.** Kernel code cannot use `<stdio.h>`, `<stdlib.h>`,
`malloc()`, `printf()`, `exit()`, or any other function from the C standard
library. Those functions ultimately depend on system calls and the C runtime,
which assume a user-space context. In kernel space, you use the kernel's own
equivalents: `kmalloc()` for memory allocation (and its safer `devm_` variants,
which you will meet in document 03), `printk()` for logging, and so on. The
kernel headers in `/lib/modules/$(uname -r)/build/include/linux/` provide all
of this.

**`printk()` instead of `printf()`.** The kernel's logging function is
`printk()`. It works like `printf()` but prefixes each message with a log level:
`KERN_INFO` for informational messages, `KERN_WARNING` for warnings,
`KERN_ERR` for errors. Messages go to the kernel ring buffer and can be read
with `dmesg`. Modern kernel code uses helper macros like `pr_info()`,
`pr_warn()`, `pr_err()`, and the device-aware `dev_info()`, `dev_err()` —
these are thin wrappers around `printk()` that add context automatically.

**No floating point.** The kernel does not save and restore the CPU's
floating-point registers on context switches (doing so for every context switch
would be prohibitively expensive). As a consequence, kernel code must not use
floating-point arithmetic. Temperature sensors typically return values in
millidegrees Celsius to work around this: instead of `23.125`, the kernel
works with `23125`. All arithmetic stays in integers.

**Memory allocation can fail, and must be checked.** In user space, the
standard library's `malloc()` almost never returns NULL in practice — the
kernel will kill other processes to free memory before letting an allocation
fail. In kernel space, allocations can and do fail, especially when memory
is fragmented or the system is under pressure. Every allocation must be
followed by a null check, and returning an appropriate error code
(`-ENOMEM`) if allocation fails is mandatory, not optional.

**Error codes are negative integers.** The kernel convention for returning
errors is to return a negative integer, where the magnitude is defined by
constants in `<linux/errno.h>`: `-ENOMEM` for out-of-memory, `-EINVAL` for
an invalid argument, `-ENODEV` for device not found, and so on. A return
value of 0 always means success. Many kernel functions return these codes,
and checking for negative return values is as fundamental as checking for
null pointers.

---

## The Module License Requirement

Every kernel module must declare a license with `MODULE_LICENSE()`. This is
not just a formality. The Linux kernel is released under the GPL (General
Public License), and the kernel enforces a distinction between modules licensed
under GPL-compatible terms and those that are not. When you load a module with
`MODULE_LICENSE("GPL")`, the kernel grants it access to a wider set of internal
symbols that are explicitly reserved for GPL-compatible code. Non-GPL modules
get a more restricted API.

For learning purposes and for any driver you share publicly, `MODULE_LICENSE("GPL")`
is the correct and expected choice. The kernel will mark itself as "tainted"
if a non-GPL module is loaded, which is also relevant if you ever file a
kernel bug report — a tainted kernel means your bug report may be dismissed
as potentially caused by the proprietary module.

---

## What Comes Next

You now have the mental model that makes kernel driver development make sense:
kernel space and user space are genuinely different environments with different
rules, modules are live code inside the running kernel, and the conventions
that look strange (no stdlib, no float, negative error codes) each exist
for a specific technical reason.

In the next document, you will write the simplest possible kernel module —
one that does nothing except print a message when loaded and when unloaded.
That minimal exercise will make the toolchain, the build process, and the
load/unload cycle feel concrete and familiar before any driver complexity
is added on top.

**Next: [02 — Your First Kernel Module](02-hello-module.md)**
