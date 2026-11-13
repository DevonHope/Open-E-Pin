/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef EPIN_BATTERY_H_
#define EPIN_BATTERY_H_

#include <stdbool.h>
#include <stdint.h>

struct battery_status {
	uint16_t mv;     /* VBAT_SYS in millivolts */
	uint8_t percent; /* 0..100, from a LiPo discharge curve */
	bool charging;   /* BQ25101 ~CHG is low */
	bool usb;        /* VBUS present */
};

int battery_init(void);

/* Take a fresh measurement, update the cached value and the Battery Service. */
int battery_measure(void);

/* Last measurement. */
struct battery_status battery_get(void);

#endif /* EPIN_BATTERY_H_ */
