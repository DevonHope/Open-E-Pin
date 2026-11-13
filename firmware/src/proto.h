/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Open E-Pin BLE protocol constants. The protocol is defined in
 * docs/ble-protocol.md; keep this file in step with it.
 */
#ifndef EPIN_PROTO_H_
#define EPIN_PROTO_H_

#define EPIN_PROTO_VERSION 1

/* 128-bit UUIDs: 7a1e000X-3c4d-4b5e-9f60-0e9e0e9e0e9e */
#define EPIN_UUID(x) BT_UUID_128_ENCODE(0x7a1e0000 + (x), 0x3c4d, 0x4b5e, 0x9f60, 0x0e9e0e9e0e9eULL)
#define EPIN_UUID_SVC     EPIN_UUID(1)
#define EPIN_UUID_INFO    EPIN_UUID(2)
#define EPIN_UUID_CONTROL EPIN_UUID(3)
#define EPIN_UUID_DATA    EPIN_UUID(4)

/* Image formats */
#define EPIN_FMT_4BPP      0x01
#define EPIN_FMT_MASK      (1u << 0)

/* Requests (app to pin) */
#define EPIN_OP_START      0x01
#define EPIN_OP_STATUS     0x02
#define EPIN_OP_COMMIT     0x03
#define EPIN_OP_ABORT      0x04
#define EPIN_OP_CLEAR      0x05
#define EPIN_OP_SLEEP      0x06
#define EPIN_OP_RESPONSE   0x80 /* OR'd with the request opcode */

/* Events (pin to app) */
#define EPIN_EVT_PROGRESS     0x90
#define EPIN_EVT_NAK          0x91
#define EPIN_EVT_REFRESH_DONE 0xA0

/* Status codes */
enum epin_status {
	EPIN_ST_OK = 0,
	EPIN_ST_BAD_LENGTH = 1,
	EPIN_ST_BAD_STATE = 2,
	EPIN_ST_CRC_MISMATCH = 3,
	EPIN_ST_BAD_FORMAT = 4,
	EPIN_ST_BUSY = 5,
	EPIN_ST_BAD_OFFSET = 6,
	EPIN_ST_LOW_BATTERY = 7,
	EPIN_ST_PANEL_ERROR = 8,
	EPIN_ST_UNKNOWN_OPCODE = 9,
};

/* Bytes between PROGRESS events */
#define EPIN_ACK_INTERVAL 4096u

/* Data packet header: u32 offset */
#define EPIN_DATA_HDR_LEN 4u

#endif /* EPIN_PROTO_H_ */
