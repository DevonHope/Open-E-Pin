/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * GDEH0169E02 command set and init sequence (JD7601 / IST7601 controller).
 *
 * Taken from Good Display's sample for this panel (EPD169_7601, an Arduino
 * and ESP-IDF port of their MSP430 reference "1D69_E6_400x400_7601_test.c").
 * The controller keeps its own waveform and resolution in OTP, so the init
 * is only a short test-mode sequence.
 */
#ifndef EPIN_EPD_CMDS_H_
#define EPIN_EPD_CMDS_H_

#include <stdint.h>

#define EPD_CMD_POF   0x02 /* power off, data 0x00 */
#define EPD_CMD_PON   0x04 /* power on, no data */
#define EPD_CMD_DSLP  0x07 /* deep sleep, data 0xA5 */
#define EPD_CMD_DTM   0x10 /* data start transmission (frame), wait BUSY before data */
#define EPD_CMD_DRF   0x12 /* display refresh, data 0x00 */
#define EPD_CMD_TSC   0x40 /* temperature read (needs a bidirectional SDA; unused) */
#define EPD_CMD_REV   0x70 /* revision read (needs a bidirectional SDA; unused) */
#define EPD_CMD_TEST  0xFF /* enter (0xA5) / exit (0xE3) test command mode */

#define EPD_DSLP_CHECK 0xA5

struct epd_init_step {
	uint8_t cmd;
	uint8_t len;
	uint8_t data[1];
};

/* INIT_IST7601() from the vendor sample, 1:1. */
static const struct epd_init_step epd_init_seq[] = {
	{ EPD_CMD_TEST, 1, { 0xA5 } }, /* enter test command mode */
	{ 0xD6,         1, { 0x00 } },
	{ EPD_CMD_TEST, 1, { 0xE3 } }, /* exit test command mode */
	{ 0xE9,         1, { 0x01 } },
};

#endif /* EPIN_EPD_CMDS_H_ */
