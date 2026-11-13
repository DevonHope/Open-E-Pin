/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Image transfer state machine: in-order chunked receive with a running
 * CRC-32, resume by image id, commit check. Plain C with no Zephyr
 * dependencies so it can be unit-tested on a PC (tests/host).
 */
#ifndef EPIN_XFER_H_
#define EPIN_XFER_H_

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum xfer_state {
	XFER_IDLE = 0,
	XFER_RECEIVING = 1,
	XFER_READY = 2,      /* all bytes in, waiting for COMMIT (reported only) */
	XFER_REFRESHING = 3, /* owned by the panel until xfer_refresh_done() */
};

/* Result of xfer_data(): what the caller should notify. */
enum xfer_data_result {
	XFER_DATA_OK = 0,   /* stored, nothing to send */
	XFER_DATA_ACK,      /* stored, send PROGRESS(offset) */
	XFER_DATA_NAK,      /* out of order, send NAK(offset) */
	XFER_DATA_DROPPED,  /* ignored, send nothing */
	XFER_DATA_ERROR,    /* bad length; status in *status */
};

struct xfer {
	uint8_t *buf;
	size_t cap;

	enum xfer_state state;
	uint8_t format;
	uint32_t len;
	uint32_t crc_expected;
	uint32_t id;

	uint32_t offset;   /* bytes received in order */
	uint32_t crc_run;  /* running CRC state (not finalised) */
	uint32_t last_ack;
	bool nak_sent;
};

/* Image size in bytes for a format, or 0 if unsupported. */
uint32_t xfer_format_size(uint8_t format);

void xfer_init(struct xfer *x, uint8_t *buf, size_t cap);

/* START. Returns an epin_status; on OK *resume_offset says where to continue. */
int xfer_start(struct xfer *x, uint8_t format, uint32_t len, uint32_t crc,
	       uint32_t id, uint32_t *resume_offset);

/* One data packet. *status is set only for XFER_DATA_ERROR. */
enum xfer_data_result xfer_data(struct xfer *x, uint32_t offset,
				const uint8_t *data, size_t n, int *status);

/* COMMIT. On OK the state becomes XFER_REFRESHING and the caller draws buf. */
int xfer_commit(struct xfer *x);

/* Panel finished drawing (whatever the outcome): back to IDLE. */
void xfer_refresh_done(struct xfer *x);

/* ABORT, or the pin is going to sleep. */
void xfer_reset(struct xfer *x);

/* State as reported over BLE: RECEIVING with every byte in reads as READY. */
static inline enum xfer_state xfer_reported_state(const struct xfer *x)
{
	if (x->state == XFER_RECEIVING && x->offset == x->len) {
		return XFER_READY;
	}
	return x->state;
}

/* Standard CRC-32 (zlib / java.util.zip.CRC32), in pieces. */
uint32_t xfer_crc32_update(uint32_t crc, const uint8_t *data, size_t n);
static inline uint32_t xfer_crc32(const uint8_t *data, size_t n)
{
	return xfer_crc32_update(0, data, n);
}

#endif /* EPIN_XFER_H_ */
