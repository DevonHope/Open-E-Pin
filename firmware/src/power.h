/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef EPIN_POWER_H_
#define EPIN_POWER_H_

#include <stdbool.h>

/* Set up the side button. on_press runs in the system work queue after
 * debouncing. Returns true when this boot was a wake-up from the button. */
int power_init(void (*on_press)(void), bool *woke_by_button);

/* Power the panel down, arm the button as the wake source and enter
 * System OFF. Does not return: the next press reboots the chip. */
FUNC_NORETURN void power_sleep(void);

#endif /* EPIN_POWER_H_ */
