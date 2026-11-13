/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <errno.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/spi.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/pm/device.h>

#include "epd.h"
#include "epd_cmds.h"

LOG_MODULE_REGISTER(epd, LOG_LEVEL_INF);

#define EPD_NODE DT_COMPAT_GET_ANY_STATUS_OKAY(gooddisplay_gdeh0169e02)

BUILD_ASSERT(DT_NODE_EXISTS(EPD_NODE), "No gooddisplay,gdeh0169e02 node in devicetree");
BUILD_ASSERT(DT_PROP(EPD_NODE, width) == EPD_WIDTH && DT_PROP(EPD_NODE, height) == EPD_HEIGHT,
	     "Panel size in devicetree does not match epd.h");

static const struct spi_dt_spec spi = SPI_DT_SPEC_GET(
	EPD_NODE, SPI_OP_MODE_MASTER | SPI_WORD_SET(8) | SPI_TRANSFER_MSB, 0);
static const struct gpio_dt_spec dc = GPIO_DT_SPEC_GET(EPD_NODE, dc_gpios);
static const struct gpio_dt_spec rst = GPIO_DT_SPEC_GET(EPD_NODE, reset_gpios);
static const struct gpio_dt_spec busy = GPIO_DT_SPEC_GET(EPD_NODE, busy_gpios);
static const struct gpio_dt_spec pwr = GPIO_DT_SPEC_GET_OR(EPD_NODE, power_gpios, {0});

/* Largest single SPI transfer; the nRF52840 SPIM DMA limit is 65535. The
 * vendor sample toggles CS around every byte; CONFIG_EPIN_EPD_CS_PER_BYTE
 * does the same if the panel turns out to need it. */
#define EPD_SPI_CHUNK (IS_ENABLED(CONFIG_EPIN_EPD_CS_PER_BYTE) ? 1 : 4096)

/* BUSY timeouts from the vendor sample. */
#define BUSY_TIMEOUT_INIT_MS    15000
#define BUSY_TIMEOUT_POWER_MS   60000
#define BUSY_TIMEOUT_REFRESH_MS (CONFIG_EPIN_EPD_BUSY_TIMEOUT_S * 1000)

static int write_bytes(const uint8_t *data, size_t len)
{
	while (len > 0) {
		size_t n = MIN(len, EPD_SPI_CHUNK);
		const struct spi_buf b = { .buf = (void *)data, .len = n };
		const struct spi_buf_set tx = { .buffers = &b, .count = 1 };
		int err = spi_write_dt(&spi, &tx);

		if (err) {
			return err;
		}
		data += n;
		len -= n;
	}
	return 0;
}

static int send_cmd(uint8_t cmd, const uint8_t *data, size_t len)
{
	int err;

	gpio_pin_set_dt(&dc, 0);
	err = write_bytes(&cmd, 1);
	if (err || len == 0) {
		return err;
	}
	gpio_pin_set_dt(&dc, 1);
	return write_bytes(data, len);
}

static int wait_idle(int32_t timeout_ms)
{
	int64_t deadline = k_uptime_get() + timeout_ms;

	k_msleep(1);
	while (gpio_pin_get_dt(&busy) == 1) {
		if (k_uptime_get() > deadline) {
			LOG_ERR("BUSY timeout");
			return -ETIMEDOUT;
		}
		k_msleep(10);
	}
	return 0;
}

/* DTM: the vendor sample waits for BUSY between the command and the frame. */
static int start_frame(void)
{
	int err = send_cmd(EPD_CMD_DTM, NULL, 0);

	err = err ? err : wait_idle(BUSY_TIMEOUT_INIT_MS);
	gpio_pin_set_dt(&dc, 1);
	return err;
}

/* Before the panel loses power: drive CS, DC and RST low and let the SPI
 * pins go to their sleep state (disconnected), so no line sits high and
 * feeds the unpowered panel through its ESD diodes. */
static void lines_low(void)
{
	(void)gpio_pin_configure_dt(&spi.config.cs.gpio, GPIO_OUTPUT_LOW);
	(void)gpio_pin_configure_dt(&dc, GPIO_OUTPUT_LOW);
	(void)gpio_pin_configure_dt(&rst, GPIO_OUTPUT_LOW);
	(void)pm_device_action_run(spi.bus, PM_DEVICE_ACTION_SUSPEND);
}

/* With the panel off: disconnect everything so nothing floats or leaks. */
static void park_pins(void)
{
	(void)pm_device_action_run(spi.bus, PM_DEVICE_ACTION_SUSPEND);
	(void)gpio_pin_configure_dt(&spi.config.cs.gpio, GPIO_DISCONNECTED);
	(void)gpio_pin_configure_dt(&dc, GPIO_DISCONNECTED);
	(void)gpio_pin_configure_dt(&rst, GPIO_DISCONNECTED);
	(void)gpio_pin_configure_dt(&busy, GPIO_DISCONNECTED);
}

int epd_setup(void)
{
	if (!spi_is_ready_dt(&spi) || !gpio_is_ready_dt(&dc) ||
	    !gpio_is_ready_dt(&rst) || !gpio_is_ready_dt(&busy)) {
		LOG_ERR("panel bus or GPIOs not ready");
		return -ENODEV;
	}
	if (pwr.port) {
		gpio_pin_configure_dt(&pwr, GPIO_OUTPUT_INACTIVE);
	}
	park_pins();
	return 0;
}

/* RESET() from the vendor sample: two low/high pulses, then wait for BUSY. */
static int reset_pulse(void)
{
	int err;

	for (int i = 0; i < 2; i++) {
		gpio_pin_set_dt(&rst, 1); /* active = RST_N low */
		k_msleep(20);
		gpio_pin_set_dt(&rst, 0);
		k_msleep(10);
	}
	err = wait_idle(BUSY_TIMEOUT_INIT_MS);
	k_msleep(10);
	return err;
}

static int power_on_and_init(void)
{
	int err;

	if (pwr.port) {
		gpio_pin_set_dt(&pwr, 1);
		k_msleep(10); /* rail and decoupling settle */
	}

	(void)pm_device_action_run(spi.bus, PM_DEVICE_ACTION_RESUME);
	gpio_pin_configure_dt(&spi.config.cs.gpio, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&dc, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&rst, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure_dt(&busy, GPIO_INPUT);

	/* The vendor bring-up resets twice, each a double 20 ms low pulse. */
	for (int i = 0; i < 2; i++) {
		err = reset_pulse();
		if (err) {
			return err;
		}
	}

	for (size_t i = 0; i < ARRAY_SIZE(epd_init_seq); i++) {
		err = send_cmd(epd_init_seq[i].cmd, epd_init_seq[i].data, epd_init_seq[i].len);
		if (err) {
			return err;
		}
	}
	return 0;
}

static int refresh_and_sleep(void)
{
	static const uint8_t zero = 0x00;
	static const uint8_t dslp = EPD_DSLP_CHECK;
	int err;

	/* Same order and delays as the vendor sample. */
	err = send_cmd(EPD_CMD_PON, NULL, 0);
	err = err ? err : wait_idle(BUSY_TIMEOUT_POWER_MS);
	k_msleep(10);
	err = err ? err : send_cmd(EPD_CMD_DRF, &zero, 1);
	k_msleep(10);
	err = err ? err : wait_idle(BUSY_TIMEOUT_REFRESH_MS);
	err = err ? err : send_cmd(EPD_CMD_POF, &zero, 1);
	err = err ? err : wait_idle(BUSY_TIMEOUT_POWER_MS);
	k_msleep(20);
	if (!err) {
		err = send_cmd(EPD_CMD_DSLP, &dslp, 1);
	}
	return err;
}

void epd_power_off(void)
{
	lines_low();
	if (pwr.port) {
		gpio_pin_set_dt(&pwr, 0);
		k_msleep(1);
	}
	park_pins();
}

int epd_show_frame(const uint8_t *frame, size_t len)
{
	int64_t t0 = k_uptime_get();
	int err;

	if (len != EPD_FRAME_BYTES) {
		return -EINVAL;
	}

	err = power_on_and_init();
	err = err ? err : start_frame();
	err = err ? err : write_bytes(frame, len);
	err = err ? err : refresh_and_sleep();
	epd_power_off();

	LOG_INF("refresh %s in %lld ms", err ? "failed" : "done", k_uptime_get() - t0);
	return err;
}

int epd_show_solid(enum epd_color color)
{
	uint8_t line[EPD_WIDTH / 2];
	int err;

	memset(line, (color << 4) | color, sizeof(line));

	err = power_on_and_init();
	err = err ? err : start_frame();
	for (int y = 0; !err && y < EPD_HEIGHT; y++) {
		err = write_bytes(line, sizeof(line));
	}
	err = err ? err : refresh_and_sleep();
	epd_power_off();
	return err;
}
