/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <string.h>

#include "proto.h"
#include "xfer.h"

#define PANEL_W 400u
#define PANEL_H 400u

uint32_t xfer_format_size(uint8_t format)
{
	switch (format) {
	case EPIN_FMT_4BPP:
		return PANEL_W * PANEL_H / 2u;
	default:
		return 0;
	}
}

/*
 * CRC-32, reflected polynomial 0xEDB88320. Nibble table: 64 bytes of flash,
 * about 2 ms for a whole 80 kB image on a 64 MHz Cortex-M4.
 */
uint32_t xfer_crc32_update(uint32_t crc, const uint8_t *data, size_t n)
{
	static const uint32_t table[16] = {
		0x00000000, 0x1db71064, 0x3b6e20c8, 0x26d930ac,
		0x76dc4190, 0x6b6b51f4, 0x4db26158, 0x5005713c,
		0xedb88320, 0xf00f9344, 0xd6d6a3e8, 0xcb61b38c,
		0x9b64c2b0, 0x86d3d2d4, 0xa00ae278, 0xbdbdf21c,
	};

	crc = ~crc;
	for (size_t i = 0; i < n; i++) {
		crc ^= data[i];
		crc = (crc >> 4) ^ table[crc & 0x0f];
		crc = (crc >> 4) ^ table[crc & 0x0f];
	}
	return ~crc;
}

void xfer_init(struct xfer *x, uint8_t *buf, size_t cap)
{
	memset(x, 0, sizeof(*x));
	x->buf = buf;
	x->cap = cap;
}

void xfer_reset(struct xfer *x)
{
	if (x->state == XFER_REFRESHING) {
		/* The panel still reads buf; xfer_refresh_done() frees it. */
		return;
	}
	xfer_init(x, x->buf, x->cap);
}

int xfer_start(struct xfer *x, uint8_t format, uint32_t len, uint32_t crc,
	       uint32_t id, uint32_t *resume_offset)
{
	uint32_t size;

	*resume_offset = 0;

	if (x->state == XFER_REFRESHING) {
		return EPIN_ST_BUSY;
	}

	size = xfer_format_size(format);
	if (size == 0) {
		return EPIN_ST_BAD_FORMAT;
	}
	if (len != size || len > x->cap) {
		return EPIN_ST_BAD_LENGTH;
	}

	if ((x->state == XFER_RECEIVING || x->state == XFER_READY) &&
	    x->format == format && x->len == len &&
	    x->crc_expected == crc && x->id == id) {
		/* Same image: resume. */
		x->nak_sent = false;
		x->last_ack = x->offset;
		*resume_offset = x->offset;
		return EPIN_ST_OK;
	}

	xfer_init(x, x->buf, x->cap);
	x->state = XFER_RECEIVING;
	x->format = format;
	x->len = len;
	x->crc_expected = crc;
	x->id = id;
	return EPIN_ST_OK;
}

enum xfer_data_result xfer_data(struct xfer *x, uint32_t offset,
				const uint8_t *data, size_t n, int *status)
{
	if (x->state != XFER_RECEIVING || n == 0) {
		return XFER_DATA_DROPPED;
	}

	if (offset != x->offset) {
		/* One NAK per gap, so the packets already in flight don't each trigger one. */
		if (x->nak_sent) {
			return XFER_DATA_DROPPED;
		}
		x->nak_sent = true;
		return XFER_DATA_NAK;
	}

	if ((uint64_t)offset + n > x->len) {
		*status = EPIN_ST_BAD_LENGTH;
		return XFER_DATA_ERROR;
	}

	memcpy(&x->buf[offset], data, n);
	x->crc_run = xfer_crc32_update(x->crc_run, data, n);
	x->offset += (uint32_t)n;
	x->nak_sent = false;

	if (x->offset == x->len || x->offset - x->last_ack >= EPIN_ACK_INTERVAL) {
		x->last_ack = x->offset;
		return XFER_DATA_ACK;
	}
	return XFER_DATA_OK;
}

int xfer_commit(struct xfer *x)
{
	if (x->state == XFER_REFRESHING) {
		return EPIN_ST_BUSY;
	}
	if (x->state != XFER_RECEIVING && x->state != XFER_READY) {
		return EPIN_ST_BAD_STATE;
	}
	if (x->offset != x->len) {
		return EPIN_ST_BAD_STATE;
	}
	if (x->crc_run != x->crc_expected) {
		xfer_init(x, x->buf, x->cap);
		return EPIN_ST_CRC_MISMATCH;
	}
	x->state = XFER_REFRESHING;
	return EPIN_ST_OK;
}

void xfer_refresh_done(struct xfer *x)
{
	xfer_init(x, x->buf, x->cap);
}
