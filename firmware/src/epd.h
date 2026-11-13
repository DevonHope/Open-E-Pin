/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
 * Driver for the Good Display GDEH0169E02 (1.69" round, 400x400, Spectra 6,
 * IST7601 / JD7601 controller) on 4-wire SPI.
 *
 * Frame format: 4 bits per pixel, two pixels per byte, left pixel in the
 * high nibble, row-major, 80 000 bytes. See docs/ble-protocol.md.
 */
#ifndef EPIN_EPD_H_
#define EPIN_EPD_H_

#include <stddef.h>
#include <stdint.h>

#define EPD_WIDTH  400
#define EPD_HEIGHT 400
#define EPD_FRAME_BYTES (EPD_WIDTH * EPD_HEIGHT / 2)

/* Panel colour codes, as in Good Display's EPD169_7601 sample (PIC_BLACK etc.). */
enum epd_color {
	EPD_BLACK = 0x0,
	EPD_WHITE = 0x1,
	EPD_YELLOW = 0x2,
	EPD_RED = 0x3,
	EPD_BLUE = 0x5,
	EPD_GREEN = 0x6,
};

/* Configure GPIOs and leave the panel unpowered. Call once at boot. */
int epd_setup(void);

/* Power, reset and initialise the panel, send a full frame, refresh, and
 * power down again. Blocks for the whole refresh (tens of seconds). */
int epd_show_frame(const uint8_t *frame, size_t len);

/* Same, but every pixel is one colour. */
int epd_show_solid(enum epd_color color);

/* Cut panel power and park its pins so nothing back-powers it. */
void epd_power_off(void);

#endif /* EPIN_EPD_H_ */
