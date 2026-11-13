/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/hwinfo.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/poweroff.h>

#include "epd.h"
#include "power.h"

LOG_MODULE_REGISTER(power, LOG_LEVEL_INF);

#define DEBOUNCE_MS 30

static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(DT_ALIAS(sw0), gpios);
static struct gpio_callback button_cb;
static void (*press_handler)(void);

static void debounce_fn(struct k_work *work)
{
	ARG_UNUSED(work);
	if (gpio_pin_get_dt(&button) == 1 && press_handler) {
		press_handler();
	}
}

static K_WORK_DELAYABLE_DEFINE(debounce_work, debounce_fn);

static void button_isr(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
	k_work_reschedule(&debounce_work, K_MSEC(DEBOUNCE_MS));
}

int power_init(void (*on_press)(void), bool *woke_by_button)
{
	uint32_t cause = 0;
	int err;

	(void)hwinfo_get_reset_cause(&cause);
	(void)hwinfo_clear_reset_cause();
	*woke_by_button = (cause & RESET_LOW_POWER_WAKE) != 0;
	LOG_INF("reset cause 0x%08x%s", cause, *woke_by_button ? " (button wake)" : "");

	if (!gpio_is_ready_dt(&button)) {
		return -ENODEV;
	}
	err = gpio_pin_configure_dt(&button, GPIO_INPUT);
	if (err) {
		return err;
	}
	press_handler = on_press;
	gpio_init_callback(&button_cb, button_isr, BIT(button.pin));
	err = gpio_add_callback(button.port, &button_cb);
	if (err) {
		return err;
	}
	return gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);
}

FUNC_NORETURN void power_sleep(void)
{
	LOG_INF("entering System OFF");
	epd_power_off();

	/* On nRF a level interrupt becomes a GPIO SENSE wake-up in System OFF. */
	(void)gpio_pin_interrupt_configure_dt(&button, GPIO_INT_LEVEL_ACTIVE);

	/* Let the log flush. */
	k_msleep(50);
	sys_poweroff();
}
