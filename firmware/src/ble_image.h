/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Open E-Pin image service: Info, Control and Data characteristics.
 * Protocol: docs/ble-protocol.md.
 */
#ifndef EPIN_BLE_IMAGE_H_
#define EPIN_BLE_IMAGE_H_

#include <stdbool.h>
#include <stdint.h>

#include "epd.h"

struct ble_image_cb {
	/* Return EPIN_ST_OK if a refresh may start now (battery check). */
	int (*can_refresh)(void);
	/* Start drawing. frame is NULL for CLEAR, then color is used. Must not
	 * block: queue the work and call ble_image_refresh_done() when finished. */
	void (*start_refresh)(const uint8_t *frame, enum epd_color color);
	/* The app asked the pin to sleep. */
	void (*sleep_requested)(void);
};

void ble_image_init(const struct ble_image_cb *cb);

/* The panel finished (status is an epin_status). Notifies REFRESH_DONE. */
void ble_image_refresh_done(int status);

/* True while the panel is drawing. */
bool ble_image_busy(void);

/* Uptime in ms of the last request or data packet. */
int64_t ble_image_last_activity(void);

/* Drop any partial transfer (before sleeping). */
void ble_image_reset(void);

#endif /* EPIN_BLE_IMAGE_H_ */
