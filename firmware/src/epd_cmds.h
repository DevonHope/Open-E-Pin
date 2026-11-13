/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * GDEH0169E02 (IST7601 / JD7601) command set and init sequence.
 *
 * Taken from Good Display's sample for this panel (EPD169_7601, ported by
 * them from their MSP430 reference 1D69_E6_400x400_7601_test.c). The IST7601
 * holds its waveform, booster and resolution settings in OTP, so the init
 * only sets one test-mode register; the rest of the sequence is
 * DTM -> PON -> DRF -> POF -> DSLP.
 */
#ifndef EPIN_EPD_CMDS_H_
#define EPIN_EPD_CMDS_H_

#include <stdint.h>

#define EPD_CMD_POF   0x02 /* power off, data 0x00 */
#define EPD_CMD_PON   0x04 /* power on */
#define EPD_CMD_DSLP  0x07 /* deep sleep, data 0xA5 */
#define EPD_CMD_DTM   0x10 /* data start transmission (DTM1) */
#define EPD_CMD_DRF   0x12 /* display refresh, data 0x00 */
#define EPD_CMD_TEST  0xFF /* 0xA5 enters test-command mode, 0xE3 leaves it */

struct epd_init_step {
	uint8_t cmd;
	uint8_t len;
	uint8_t data[1];
};

/* INIT_IST7601() from the vendor sample, byte for byte. */
static const struct epd_init_step epd_init_seq[] = {
	{ EPD_CMD_TEST, 1, { 0xA5 } }, /* enter test commands */
	{ 0xD6,         1, { 0x00 } },
	{ EPD_CMD_TEST, 1, { 0xE3 } }, /* leave test commands */
	{ 0xE9,         1, { 0x01 } },
};

#endif /* EPIN_EPD_CMDS_H_ */
