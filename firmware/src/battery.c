/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <zephyr/bluetooth/services/bas.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#if defined(CONFIG_SOC_SERIES_NRF52X)
#include <hal/nrf_power.h>
#endif

#include "battery.h"

LOG_MODULE_REGISTER(battery, LOG_LEVEL_INF);

#define USER_NODE DT_PATH(zephyr_user)

static const struct adc_dt_spec vbat = ADC_DT_SPEC_GET(USER_NODE);
static const struct gpio_dt_spec chg = GPIO_DT_SPEC_GET_OR(USER_NODE, chg_gpios, {0});

/* VBAT_SYS feeds the ADC through 10M / 10M. */
#define DIVIDER_NUM 2
#define DIVIDER_DEN 1

static struct battery_status cached;
static K_MUTEX_DEFINE(lock);

/* Resting-voltage curve for a small LiPo, in mV and percent. Light load. */
static const struct {
	uint16_t mv;
	uint8_t pct;
} curve[] = {
	{ 4180, 100 }, { 4100, 92 }, { 4000, 80 }, { 3900, 66 }, { 3800, 50 },
	{ 3750, 40 },  { 3700, 30 }, { 3650, 20 }, { 3600, 12 }, { 3500, 5 },
	{ 3300, 0 },
};

static uint8_t mv_to_percent(int mv)
{
	if (mv >= curve[0].mv) {
		return 100;
	}
	for (size_t i = 1; i < ARRAY_SIZE(curve); i++) {
		if (mv >= curve[i].mv) {
			int span_mv = curve[i - 1].mv - curve[i].mv;
			int span_pct = curve[i - 1].pct - curve[i].pct;

			return curve[i].pct + (mv - curve[i].mv) * span_pct / span_mv;
		}
	}
	return 0;
}

int battery_init(void)
{
	int err;

	if (!adc_is_ready_dt(&vbat)) {
		LOG_ERR("ADC not ready");
		return -ENODEV;
	}
	err = adc_channel_setup_dt(&vbat);
	if (err) {
		return err;
	}
	if (chg.port) {
		err = gpio_pin_configure_dt(&chg, GPIO_INPUT);
		if (err) {
			return err;
		}
	}
	return battery_measure();
}

int battery_measure(void)
{
	int16_t sample = 0;
	struct adc_sequence seq = {
		.buffer = &sample,
		.buffer_size = sizeof(sample),
	};
	struct battery_status s = { 0 };
	int32_t mv;
	int err;

	adc_sequence_init_dt(&vbat, &seq);
	err = adc_read_dt(&vbat, &seq);
	if (err) {
		LOG_ERR("ADC read failed (%d)", err);
		return err;
	}

	mv = MAX(sample, 0);
	err = adc_raw_to_millivolts_dt(&vbat, &mv);
	if (err) {
		return err;
	}
	mv = mv * DIVIDER_NUM / DIVIDER_DEN;

	s.mv = (uint16_t)CLAMP(mv, 0, UINT16_MAX);
	s.percent = mv_to_percent(mv);
	s.charging = chg.port ? gpio_pin_get_dt(&chg) == 1 : false;
#if defined(CONFIG_SOC_SERIES_NRF52X) && NRF_POWER_HAS_USBREG
	s.usb = nrf_power_usbregstatus_vbusdet_get(NRF_POWER);
#endif

	k_mutex_lock(&lock, K_FOREVER);
	cached = s;
	k_mutex_unlock(&lock);

	bt_bas_set_battery_level(s.percent);
	LOG_INF("battery %u mV, %u%%%s%s", s.mv, s.percent,
		s.charging ? ", charging" : "", s.usb ? ", USB" : "");
	return 0;
}

struct battery_status battery_get(void)
{
	struct battery_status s;

	k_mutex_lock(&lock, K_FOREVER);
	s = cached;
	k_mutex_unlock(&lock);
	return s;
}
