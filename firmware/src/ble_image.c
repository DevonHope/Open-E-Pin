/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/uuid.h>
#include <zephyr/kernel.h>
#include <zephyr/logging/log.h>
#include <zephyr/sys/byteorder.h>

#include <app_version.h>

#include "battery.h"
#include "ble_image.h"
#include "epd.h"
#include "proto.h"
#include "xfer.h"

LOG_MODULE_REGISTER(ble_image, LOG_LEVEL_INF);

static struct bt_uuid_128 svc_uuid = BT_UUID_INIT_128(EPIN_UUID_SVC);
static struct bt_uuid_128 info_uuid = BT_UUID_INIT_128(EPIN_UUID_INFO);
static struct bt_uuid_128 ctrl_uuid = BT_UUID_INIT_128(EPIN_UUID_CONTROL);
static struct bt_uuid_128 data_uuid = BT_UUID_INIT_128(EPIN_UUID_DATA);

/* The whole frame lives in RAM (80 kB of 256 kB) so a dropped link can resume. */
static uint8_t frame[EPD_FRAME_BYTES];
static struct xfer xfer;
static K_MUTEX_DEFINE(lock);

static const struct ble_image_cb *cbs;
static bool clearing; /* CLEAR in progress (xfer stays idle) */
static int64_t last_activity;

static ssize_t read_info(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			 void *buf, uint16_t len, uint16_t offset);
static ssize_t write_ctrl(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  const void *buf, uint16_t len, uint16_t offset, uint8_t flags);
static ssize_t write_data(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  const void *buf, uint16_t len, uint16_t offset, uint8_t flags);

BT_GATT_SERVICE_DEFINE(epin_svc,
	BT_GATT_PRIMARY_SERVICE(&svc_uuid),
	BT_GATT_CHARACTERISTIC(&info_uuid.uuid, BT_GATT_CHRC_READ,
			       BT_GATT_PERM_READ, read_info, NULL, NULL),
	BT_GATT_CHARACTERISTIC(&ctrl_uuid.uuid, BT_GATT_CHRC_WRITE | BT_GATT_CHRC_NOTIFY,
			       BT_GATT_PERM_WRITE, NULL, write_ctrl, NULL),
	BT_GATT_CCC(NULL, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
	BT_GATT_CHARACTERISTIC(&data_uuid.uuid, BT_GATT_CHRC_WRITE_WITHOUT_RESP,
			       BT_GATT_PERM_WRITE, NULL, write_data, NULL),
);

/* Attribute index of the Control value, for notifications. */
#define CTRL_ATTR (&epin_svc.attrs[4])

static void notify(struct bt_conn *conn, const uint8_t *msg, size_t len)
{
	int err = bt_gatt_notify(conn, CTRL_ATTR, msg, len);

	if (err && err != -ENOTCONN) {
		LOG_WRN("notify 0x%02x failed (%d)", msg[0], err);
	}
}

static void respond(struct bt_conn *conn, uint8_t op, uint8_t status,
		    const uint8_t *payload, size_t plen)
{
	uint8_t msg[2 + 8];

	__ASSERT_NO_MSG(plen <= 8);
	msg[0] = EPIN_OP_RESPONSE | op;
	msg[1] = status;
	memcpy(&msg[2], payload, plen);
	notify(conn, msg, 2 + plen);
}

static void event_u32(struct bt_conn *conn, uint8_t evt, uint32_t value)
{
	uint8_t msg[5] = { evt };

	sys_put_le32(value, &msg[1]);
	notify(conn, msg, sizeof(msg));
}

static bool panel_busy_locked(void)
{
	return clearing || xfer.state == XFER_REFRESHING;
}

static ssize_t read_info(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			 void *buf, uint16_t len, uint16_t offset)
{
	struct battery_status bat = battery_get();
	uint8_t info[16] = { 0 };
	uint8_t state;

	k_mutex_lock(&lock, K_FOREVER);
	state = clearing ? XFER_REFRESHING : xfer_reported_state(&xfer);
	k_mutex_unlock(&lock);

	info[0] = EPIN_PROTO_VERSION;
	info[1] = CONFIG_EPIN_HW_REV;
	sys_put_le16(EPD_WIDTH, &info[2]);
	sys_put_le16(EPD_HEIGHT, &info[4]);
	info[6] = EPIN_FMT_MASK;
	info[7] = state;
	sys_put_le16(bat.mv, &info[8]);
	info[10] = bat.percent;
	info[11] = (bat.charging ? BIT(0) : 0) | (bat.usb ? BIT(1) : 0);
	info[12] = APP_VERSION_MAJOR;
	info[13] = APP_VERSION_MINOR;
	info[14] = APP_PATCHLEVEL;

	return bt_gatt_attr_read(conn, attr, buf, len, offset, info, sizeof(info));
}

static bool valid_color(uint8_t c)
{
	switch (c) {
	case EPD_BLACK: case EPD_WHITE: case EPD_YELLOW:
	case EPD_RED: case EPD_BLUE: case EPD_GREEN:
		return true;
	default:
		return false;
	}
}

static ssize_t write_ctrl(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  const void *buf, uint16_t len, uint16_t offset, uint8_t flags)
{
	const uint8_t *p = buf;
	uint8_t out[5];
	uint32_t resume;
	int st;

	if (offset != 0) {
		return BT_GATT_ERR(BT_ATT_ERR_INVALID_OFFSET);
	}
	if (len < 1) {
		return BT_GATT_ERR(BT_ATT_ERR_INVALID_ATTRIBUTE_LEN);
	}

	k_mutex_lock(&lock, K_FOREVER);
	last_activity = k_uptime_get();

	switch (p[0]) {
	case EPIN_OP_START:
		if (len != 14) {
			st = EPIN_ST_BAD_LENGTH;
			resume = 0;
		} else if (clearing) {
			st = EPIN_ST_BUSY;
			resume = 0;
		} else {
			st = xfer_start(&xfer, p[1], sys_get_le32(&p[2]), sys_get_le32(&p[6]),
					sys_get_le32(&p[10]), &resume);
		}
		LOG_INF("START len %u id 0x%08x: status %d, offset %u",
			len == 14 ? sys_get_le32(&p[2]) : 0, len == 14 ? sys_get_le32(&p[10]) : 0,
			st, resume);
		sys_put_le32(resume, out);
		respond(conn, EPIN_OP_START, st, out, 4);
		break;

	case EPIN_OP_STATUS:
		out[0] = clearing ? XFER_REFRESHING : xfer_reported_state(&xfer);
		sys_put_le32(xfer.offset, &out[1]);
		respond(conn, EPIN_OP_STATUS, EPIN_ST_OK, out, 5);
		break;

	case EPIN_OP_COMMIT:
		if (panel_busy_locked()) {
			st = EPIN_ST_BUSY;
		} else if (xfer_reported_state(&xfer) != XFER_READY) {
			st = EPIN_ST_BAD_STATE;
		} else {
			st = cbs->can_refresh();
			if (st == EPIN_ST_OK) {
				st = xfer_commit(&xfer);
			}
		}
		LOG_INF("COMMIT: status %d", st);
		respond(conn, EPIN_OP_COMMIT, st, NULL, 0);
		if (st == EPIN_ST_OK) {
			cbs->start_refresh(frame, EPD_WHITE);
		}
		break;

	case EPIN_OP_ABORT:
		xfer_reset(&xfer);
		respond(conn, EPIN_OP_ABORT, EPIN_ST_OK, NULL, 0);
		break;

	case EPIN_OP_CLEAR:
		if (len != 2 || !valid_color(p[1])) {
			st = EPIN_ST_BAD_FORMAT;
		} else if (panel_busy_locked()) {
			st = EPIN_ST_BUSY;
		} else {
			st = cbs->can_refresh();
		}
		respond(conn, EPIN_OP_CLEAR, st, NULL, 0);
		if (st == EPIN_ST_OK) {
			xfer_reset(&xfer);
			clearing = true;
			cbs->start_refresh(NULL, (enum epd_color)p[1]);
		}
		break;

	case EPIN_OP_SLEEP:
		respond(conn, EPIN_OP_SLEEP, EPIN_ST_OK, NULL, 0);
		cbs->sleep_requested();
		break;

	default:
		respond(conn, p[0] & ~EPIN_OP_RESPONSE, EPIN_ST_UNKNOWN_OPCODE, NULL, 0);
		break;
	}

	k_mutex_unlock(&lock);
	return len;
}

static ssize_t write_data(struct bt_conn *conn, const struct bt_gatt_attr *attr,
			  const void *buf, uint16_t len, uint16_t offset, uint8_t flags)
{
	const uint8_t *p = buf;
	enum xfer_data_result r;
	uint32_t at;
	int st = EPIN_ST_OK;

	if (offset != 0 || len <= EPIN_DATA_HDR_LEN) {
		return BT_GATT_ERR(BT_ATT_ERR_INVALID_ATTRIBUTE_LEN);
	}

	k_mutex_lock(&lock, K_FOREVER);
	last_activity = k_uptime_get();
	r = xfer_data(&xfer, sys_get_le32(p), p + EPIN_DATA_HDR_LEN,
		      len - EPIN_DATA_HDR_LEN, &st);
	at = xfer.offset;
	k_mutex_unlock(&lock);

	switch (r) {
	case XFER_DATA_ACK:
		event_u32(conn, EPIN_EVT_PROGRESS, at);
		break;
	case XFER_DATA_NAK:
		LOG_WRN("out of order at %u, expected %u", sys_get_le32(p), at);
		event_u32(conn, EPIN_EVT_NAK, at);
		break;
	case XFER_DATA_ERROR:
		LOG_WRN("data packet rejected (status %d)", st);
		break;
	default:
		break;
	}
	return len;
}

void ble_image_init(const struct ble_image_cb *cb)
{
	cbs = cb;
	xfer_init(&xfer, frame, sizeof(frame));
	last_activity = k_uptime_get();
}

void ble_image_refresh_done(int status)
{
	uint8_t msg[2] = { EPIN_EVT_REFRESH_DONE, (uint8_t)status };

	k_mutex_lock(&lock, K_FOREVER);
	clearing = false;
	if (xfer.state == XFER_REFRESHING) {
		xfer_refresh_done(&xfer);
	}
	last_activity = k_uptime_get();
	k_mutex_unlock(&lock);

	notify(NULL, msg, sizeof(msg));
}

bool ble_image_busy(void)
{
	bool busy;

	k_mutex_lock(&lock, K_FOREVER);
	busy = panel_busy_locked();
	k_mutex_unlock(&lock);
	return busy;
}

int64_t ble_image_last_activity(void)
{
	return last_activity;
}

void ble_image_reset(void)
{
	k_mutex_lock(&lock, K_FOREVER);
	xfer_reset(&xfer);
	k_mutex_unlock(&lock);
}
