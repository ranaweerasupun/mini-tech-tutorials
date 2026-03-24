/*
 * hello.c — The simplest possible Linux kernel module.
 *
 * This module does nothing useful. Its purpose is to make the
 * kernel module build process, the load/unload cycle, and `dmesg`
 * logging feel concrete before any driver complexity is introduced.
 *
 * Study this alongside docs/02-hello-module.md.
 *
 * Build:  make
 * Load:   sudo insmod hello.ko
 * Check:  dmesg | tail -5
 * Unload: sudo rmmod hello
 *
 * SPDX-License-Identifier: GPL-2.0
 */

#include <linux/module.h>    /* Required for every kernel module */
#include <linux/init.h>      /* Required for __init and __exit */
#include <linux/kernel.h>    /* Required for pr_info() */

/*
 * __init tells the compiler (and the kernel) that this function is
 * only needed during module initialisation. Once the module is loaded
 * and init returns, the kernel can reclaim the memory this function
 * occupied. You will see __init on every module init function.
 */
static int __init hello_init(void)
{
    /*
     * pr_info() is the kernel's equivalent of printf() at INFO level.
     * Output goes to the kernel ring buffer, not your terminal.
     * Read it with: dmesg | tail -5
     *
     * There is no newline required before the message — the ring buffer
     * handles line separation. The trailing \n is still conventional.
     */
    pr_info("Hello from kernel space! Module loaded successfully.\n");

    /*
     * Returning 0 from the init function signals success.
     * Any non-zero return tells insmod the load failed, and the module
     * is not added to the running kernel.
     * Try changing this to `return -EINVAL;` and observe what insmod reports.
     */
    return 0;
}

/*
 * __exit marks this function as cleanup-only code. If the module were
 * compiled directly into the kernel rather than as a loadable .ko, this
 * function would never be called and the compiler would discard it.
 */
static void __exit hello_exit(void)
{
    pr_info("Goodbye from kernel space! Module unloaded.\n");
    /* No return value — exit functions return void */
}

/*
 * These two macros register hello_init and hello_exit as the module's
 * entry and exit points. The kernel calls hello_init when you run
 * `insmod hello.ko`, and hello_exit when you run `rmmod hello`.
 */
module_init(hello_init);
module_exit(hello_exit);

/*
 * Module metadata. MODULE_LICENSE("GPL") is particularly important:
 * it grants the module access to GPL-only kernel symbols and prevents
 * the kernel from being marked as "tainted" when the module is loaded.
 */
MODULE_LICENSE("GPL");
MODULE_AUTHOR("Your Name");
MODULE_DESCRIPTION("Minimal kernel module — for learning the build and load cycle");
MODULE_VERSION("1.0");
