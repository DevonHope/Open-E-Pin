/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Open E-Pin firmware: wake on button, advertise, receive an image over BLE,
 * draw it on the round e-paper panel, go back to System OFF.
 */
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gap.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>

#include <app_version.h>

#include "battery.h"
#include "ble_image.h"
#include "epd.h"
#include "power.h"
#include "proto.h"

LOG_MODULE_REGISTER(main, LOG_LEVEL_INF);

/* An idle connection is dropped after this long, so a forgotten app can't
 * keep the pin awake. */
#define CONN_IDLE_TIMEOUT_MS (120 * 1000)

static const struct bt_data ad[] = {
	BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
	BT_DATA(BT_DATA_NAME_COMPLETE, CONFIG_BT_DEVICE_NAME, sizeof(CONFIG_BT_DEVICE_NAME) - 1),
};

static const struct bt_data sd[] = {
	BT_DATA_BYTES(BT_DATA_UUID128_ALL, EPIN_UUID_SVC),
};

static struct bt_conn *current_conn;
static bool advertising;
static bool sleep_asap; /* the app sent SLEEP */

/* ---- sleep ------------------------------------------------------------ */

static void sleep_fn(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(sleep_work, sleep_fn);

static void schedule_sleep(int seconds)
{
	k_work_reschedule(&sleep_work, K_SECONDS(seconds));
}

static void sleep_fn(struct k_work *work)
{
	ARG_UNUSED(work);

	if (current_conn || ble_image_busy()) {
		/* Disconnect and refresh-done both reschedule. */
		return;
	}
	if (advertising) {
		(void)bt_le_adv_stop();
		advertising = false;
	}
	ble_image_reset();
	power_sleep();
}

/* ---- advertising ------------------------------------------------------ */

static void start_advertising(void)
{
	const struct bt_le_adv_param *param = BT_LE_ADV_PARAM(
		BT_LE_ADV_OPT_CONN, BT_GAP_ADV_FAST_INT_MIN_2, BT_GAP_ADV_FAST_INT_MAX_2, NULL);
	int err;

	if (advertising || current_conn) {
		return;
	}
	err = bt_le_adv_start(param, ad, ARRAY_SIZE(ad), sd, ARRAY_SIZE(sd));
	if (err) {
		LOG_ERR("advertising failed (%d)", err);
		return;
	}
	advertising = true;
	LOG_INF("advertising");
}

/* ---- connection ------------------------------------------------------- */

static void connected(struct bt_conn *conn, uint8_t err)
{
	if (err) {
		LOG_WRN("connection failed (0x%02x)", err);
		advertising = false;
		start_advertising();
		return;
	}
	LOG_INF("connected");
	advertising = false; /* connectable advertising stops on connect */
	current_conn = bt_conn_ref(conn);
	k_work_cancel_delayable(&sleep_work);

	/* Fast transfer: 2M PHY and long data packets. The app also asks. */
	(void)bt_conn_le_phy_update(conn, BT_CONN_LE_PHY_PARAM_2M);
	(void)bt_conn_le_data_len_update(conn, BT_LE_DATA_LEN_PARAM_MAX);

	(void)battery_measure();
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	LOG_INF("disconnected (0x%02x)", reason);
	if (current_conn) {
		bt_conn_unref(current_conn);
		current_conn = NULL;
	}
	/* Keep advertising for a while so an interrupted upload can resume. */
	if (sleep_asap) {
		schedule_sleep(1);
		return;
	}
	start_advertising();
	schedule_sleep(CONFIG_EPIN_IDLE_TIMEOUT_S);
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
	.connected = connected,
	.disconnected = disconnected,
};

/* ---- panel refresh ---------------------------------------------------- */

#define REFRESH_STACK_SIZE 2048
#define REFRESH_PRIORITY   K_LOWEST_APPLICATION_THREAD_PRIO
K_THREAD_STACK_DEFINE(refresh_stack, REFRESH_STACK_SIZE);
static struct k_work_q refresh_q;

static const uint8_t *refresh_frame;
static enum epd_color refresh_color;

static void refresh_fn(struct k_work *work)
{
	int err;

	ARG_UNUSED(work);
	if (refresh_frame) {
		err = epd_show_frame(refresh_frame, EPD_FRAME_BYTES);
	} else {
		err = epd_show_solid(refresh_color);
	}
	ble_image_refresh_done(err ? EPIN_ST_PANEL_ERROR : EPIN_ST_OK);
	(void)battery_measure();

	if (!current_conn) {
		schedule_sleep(CONFIG_EPIN_IDLE_TIMEOUT_S);
	}
}

static K_WORK_DEFINE(refresh_work, refresh_fn);

static int can_refresh(void)
{
	(void)battery_measure();
	if (battery_get().mv < CONFIG_EPIN_MIN_REFRESH_MV && !battery_get().usb) {
		return EPIN_ST_LOW_BATTERY;
	}
	return EPIN_ST_OK;
}

static void start_refresh(const uint8_t *frame, enum epd_color color)
{
	refresh_frame = frame;
	refresh_color = color;
	k_work_submit_to_queue(&refresh_q, &refresh_work);
}

static void disconnect_fn(struct k_work *work)
{
	ARG_UNUSED(work);
	if (current_conn) {
		(void)bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
	}
}

static K_WORK_DELAYABLE_DEFINE(disconnect_work, disconnect_fn);

static void sleep_requested(void)
{
	/* Give the response notification time to go out, then hang up. The
	 * disconnect handler then sleeps within a second. */
	sleep_asap = true;
	k_work_reschedule(&disconnect_work, K_MSEC(200));
}

static const struct ble_image_cb image_cb = {
	.can_refresh = can_refresh,
	.start_refresh = start_refresh,
	.sleep_requested = sleep_requested,
};

/* ---- button and housekeeping ------------------------------------------ */

static void on_button(void)
{
	LOG_INF("button");
	if (!current_conn) {
		start_advertising();
		schedule_sleep(CONFIG_EPIN_ADV_TIMEOUT_S);
	}
}

static void housekeeping_fn(struct k_work *work);
static K_WORK_DELAYABLE_DEFINE(housekeeping_work, housekeeping_fn);

static void housekeeping_fn(struct k_work *work)
{
	ARG_UNUSED(work);
	(void)battery_measure();

	if (current_conn && !ble_image_busy() &&
	    k_uptime_get() - ble_image_last_activity() > CONN_IDLE_TIMEOUT_MS) {
		LOG_INF("connection idle, disconnecting");
		(void)bt_conn_disconnect(current_conn, BT_HCI_ERR_REMOTE_USER_TERM_CONN);
	}
	k_work_reschedule(&housekeeping_work, K_SECONDS(CONFIG_EPIN_BATTERY_POLL_S));
}

int main(void)
{
	bool woke_by_button = false;
	int err;

	LOG_INF("Open E-Pin firmware %s", APP_VERSION_STRING);

	err = epd_setup();
	if (err) {
		LOG_ERR("panel setup failed (%d)", err);
	}
	err = power_init(on_button, &woke_by_button);
	if (err) {
		LOG_ERR("button setup failed (%d)", err);
	}

	k_work_queue_start(&refresh_q, refresh_stack, K_THREAD_STACK_SIZEOF(refresh_stack),
			   REFRESH_PRIORITY, NULL);

	err = bt_enable(NULL);
	if (err) {
		LOG_ERR("Bluetooth init failed (%d)", err);
		power_sleep();
	}

	err = battery_init();
	if (err) {
		LOG_ERR("battery init failed (%d)", err);
	}

	ble_image_init(&image_cb);

	/* Both a button wake and a first power-up (battery plugged in, or a
	 * reset from the debugger) open the advertising window. */
	start_advertising();
	schedule_sleep(CONFIG_EPIN_ADV_TIMEOUT_S);
	k_work_reschedule(&housekeeping_work, K_SECONDS(CONFIG_EPIN_BATTERY_POLL_S));

	return 0;
}
