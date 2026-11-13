# SPDX-License-Identifier: GPL-3.0-or-later
cmake_minimum_required(VERSION 3.20.0)

# The custom board lives in this repository, under boards/.
list(APPEND BOARD_ROOT ${CMAKE_CURRENT_SOURCE_DIR})
# Devicetree binding for the panel.
list(APPEND DTS_ROOT ${CMAKE_CURRENT_SOURCE_DIR})

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(open_e_pin)

target_sources(app PRIVATE
	src/main.c
	src/ble_image.c
	src/xfer.c
	src/epd.c
	src/battery.c
	src/power.c
)
