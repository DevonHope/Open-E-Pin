/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * GDEH0169E02 command set and init sequence.
 *
 * !!! UNVERIFIED PLACEHOLDER !!!
 * The panel specification lists pins and timings but not the command set.
 * The values below are the init sequence Good Display uses for its other
 * Spectra 6 panels (GDEP073E01 family), with the resolution changed to
 * 400x400. Replace them with the sequence from Good Display's ESP32 sample
 * code for the GDEH0169E02 (link in hardware/README.md) before the first
 * power-up of a real panel. Wrong booster settings can stress the panel.
 */
#ifndef EPIN_EPD_CMDS_H_
#define EPIN_EPD_CMDS_H_

#include <stdint.h>

#define EPD_CMD_PSR   0x00 /* panel setting */
#define EPD_CMD_PWR   0x01 /* power setting */
#define EPD_CMD_POF   0x02 /* power off */
#define EPD_CMD_POFS  0x03 /* power off sequence */
#define EPD_CMD_PON   0x04 /* power on */
#define EPD_CMD_BTST1 0x05
#define EPD_CMD_BTST2 0x06
#define EPD_CMD_DSLP  0x07 /* deep sleep, data 0xA5 */
#define EPD_CMD_BTST3 0x08
#define EPD_CMD_DTM   0x10 /* data start transmission */
#define EPD_CMD_DRF   0x12 /* display refresh */
#define EPD_CMD_PLL   0x30
#define EPD_CMD_CDI   0x50 /* VCOM and data interval */
#define EPD_CMD_TCON  0x60
#define EPD_CMD_TRES  0x61 /* resolution */
#define EPD_CMD_T_VDCS 0x84
#define EPD_CMD_PWS   0xE3
#define EPD_CMD_CMDH  0xAA

struct epd_init_step {
	uint8_t cmd;
	uint8_t len;
	uint8_t data[6];
};

static const struct epd_init_step epd_init_seq[] = {
	{ EPD_CMD_CMDH,  6, { 0x49, 0x55, 0x20, 0x08, 0x09, 0x18 } },
	{ EPD_CMD_PWR,   1, { 0x3F } },
	{ EPD_CMD_PSR,   2, { 0x5F, 0x69 } },
	{ EPD_CMD_POFS,  4, { 0x00, 0x54, 0x00, 0x44 } },
	{ EPD_CMD_BTST1, 4, { 0x40, 0x1F, 0x1F, 0x2C } },
	{ EPD_CMD_BTST2, 4, { 0x6F, 0x1F, 0x17, 0x49 } },
	{ EPD_CMD_BTST3, 4, { 0x6F, 0x1F, 0x1F, 0x22 } },
	{ EPD_CMD_PLL,   1, { 0x08 } },
	{ EPD_CMD_CDI,   1, { 0x3F } },
	{ EPD_CMD_TCON,  2, { 0x02, 0x00 } },
	{ EPD_CMD_TRES,  4, { 0x01, 0x90, 0x01, 0x90 } }, /* 400 x 400 */
	{ EPD_CMD_T_VDCS, 1, { 0x01 } },
	{ EPD_CMD_PWS,   1, { 0x2F } },
};

#endif /* EPIN_EPD_CMDS_H_ */
