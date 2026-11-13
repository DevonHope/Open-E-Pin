/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Host unit tests for src/xfer.c (no Zephyr needed):
 *   cc -std=c99 -Wall -Wextra -I../../src test_xfer.c ../../src/xfer.c -o test_xfer && ./test_xfer
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "proto.h"
#include "xfer.h"

#define LEN 80000u
#define MTU_PAYLOAD 240u

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

static uint8_t image[LEN];
static uint8_t frame[LEN];

static uint32_t send_range(struct xfer *x, uint32_t from, uint32_t to, int *acks)
{
	int st;

	for (uint32_t off = from; off < to; off += MTU_PAYLOAD) {
		uint32_t n = to - off < MTU_PAYLOAD ? to - off : MTU_PAYLOAD;
		enum xfer_data_result r = xfer_data(x, off, &image[off], n, &st);

		if (r == XFER_DATA_ACK && acks) {
			(*acks)++;
		}
		if (r != XFER_DATA_OK && r != XFER_DATA_ACK) {
			return off;
		}
	}
	return to;
}

static void test_crc(void)
{
	/* Standard check value for "123456789". */
	CHECK(xfer_crc32((const uint8_t *)"123456789", 9) == 0xCBF43926u);
	/* Piecewise equals whole. */
	uint32_t c = xfer_crc32_update(0, (const uint8_t *)"1234", 4);
	c = xfer_crc32_update(c, (const uint8_t *)"56789", 5);
	CHECK(c == 0xCBF43926u);
}

static void test_full_transfer(void)
{
	struct xfer x;
	uint32_t crc = xfer_crc32(image, LEN), off;
	int acks = 0;

	xfer_init(&x, frame, sizeof(frame));
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 1, &off) == EPIN_ST_OK && off == 0);
	CHECK(xfer_commit(&x) == EPIN_ST_BAD_STATE);
	CHECK(send_range(&x, 0, LEN, &acks) == LEN);
	/* One PROGRESS per 4096 bytes or more, plus one at the end. */
	CHECK(acks >= 2 && acks <= (int)(LEN / EPIN_ACK_INTERVAL) + 1);
	CHECK(x.last_ack == LEN);
	CHECK(xfer_reported_state(&x) == XFER_READY);
	CHECK(xfer_commit(&x) == EPIN_ST_OK);
	CHECK(x.state == XFER_REFRESHING);
	CHECK(memcmp(frame, image, LEN) == 0);
	/* Busy while refreshing. */
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 2, &off) == EPIN_ST_BUSY);
	xfer_reset(&x);
	CHECK(x.state == XFER_REFRESHING);
	xfer_refresh_done(&x);
	CHECK(x.state == XFER_IDLE);
}

static void test_resume(void)
{
	struct xfer x;
	uint32_t crc = xfer_crc32(image, LEN), off;

	xfer_init(&x, frame, sizeof(frame));
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 7, &off) == EPIN_ST_OK);
	send_range(&x, 0, 30000, NULL);
	/* Link drops; app reconnects with the same image. */
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 7, &off) == EPIN_ST_OK);
	CHECK(off == x.offset && off >= 30000 - MTU_PAYLOAD);
	CHECK(send_range(&x, off, LEN, NULL) == LEN);
	CHECK(xfer_commit(&x) == EPIN_ST_OK);
	xfer_refresh_done(&x);

	/* A different id starts over. */
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 7, &off) == EPIN_ST_OK && off == 0);
	send_range(&x, 0, 5000, NULL);
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 8, &off) == EPIN_ST_OK && off == 0);
}

static void test_out_of_order(void)
{
	struct xfer x;
	uint32_t crc = xfer_crc32(image, LEN), off;
	int st;

	xfer_init(&x, frame, sizeof(frame));
	xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 3, &off);
	send_range(&x, 0, 960, NULL);
	/* Skip a packet: one NAK, then silence for the rest in flight. */
	CHECK(xfer_data(&x, 1200, &image[1200], 240, &st) == XFER_DATA_NAK);
	CHECK(xfer_data(&x, 1440, &image[1440], 240, &st) == XFER_DATA_DROPPED);
	CHECK(x.offset == 960);
	/* Rewind to the expected offset and finish. */
	CHECK(send_range(&x, 960, LEN, NULL) == LEN);
	CHECK(xfer_commit(&x) == EPIN_ST_OK);
}

static void test_errors(void)
{
	struct xfer x;
	uint32_t crc = xfer_crc32(image, LEN), off;
	int st = 0;

	xfer_init(&x, frame, sizeof(frame));
	CHECK(xfer_start(&x, 0x7f, LEN, crc, 1, &off) == EPIN_ST_BAD_FORMAT);
	CHECK(xfer_start(&x, EPIN_FMT_4BPP, LEN - 1, crc, 1, &off) == EPIN_ST_BAD_LENGTH);
	/* Data before START is ignored. */
	CHECK(xfer_data(&x, 0, image, 10, &st) == XFER_DATA_DROPPED);
	/* Packet past the end. */
	xfer_start(&x, EPIN_FMT_4BPP, LEN, crc, 1, &off);
	send_range(&x, 0, LEN - 100, NULL);
	off = x.offset;
	CHECK(xfer_data(&x, off, image, LEN - off + 1, &st) == XFER_DATA_ERROR && st == EPIN_ST_BAD_LENGTH);
	/* Wrong CRC: commit fails and the transfer is dropped. */
	xfer_start(&x, EPIN_FMT_4BPP, LEN, crc ^ 1, 9, &off);
	send_range(&x, 0, LEN, NULL);
	CHECK(xfer_commit(&x) == EPIN_ST_CRC_MISMATCH);
	CHECK(x.state == XFER_IDLE);
}

int main(void)
{
	srand(1234);
	for (size_t i = 0; i < LEN; i++) {
		image[i] = (uint8_t)rand();
	}
	test_crc();
	test_full_transfer();
	test_resume();
	test_out_of_order();
	test_errors();
	if (failures) {
		printf("%d check(s) failed\n", failures);
		return 1;
	}
	printf("xfer: all tests passed\n");
	return 0;
}
