# Open E-Pin firmware

Firmware for the Open E-Pin board (Raytac MDBT50Q-1MV2, nRF52840). It sleeps until the side
button is pressed, advertises over Bluetooth LE, receives an image from the Android app,
draws it on the round GDEH0169E02 e-paper panel and goes back to sleep. The BLE protocol
is in [`docs/ble-protocol.md`](../docs/ble-protocol.md).

**Status: framework.** It builds for the pin board and for an nRF52840 DK, and the transfer
logic has unit tests. It has not run on a panel yet; see [Before the first power-up](#before-the-first-power-up-of-a-real-panel).

## Why Zephyr / nRF Connect SDK

- It is Nordic's supported SDK for the nRF52840. The older nRF5 SDK is in maintenance
  mode, and the Arduino cores trail behind on the radio stack and power management.
- The custom board is described in devicetree ([`boards/openepin/open_e_pin`](boards/openepin/open_e_pin)),
  so the pin map lives in one file, and the same app runs on an nRF52840 DK for bench work.
- System OFF with a GPIO wake-up, the SAADC, SPI with DMA and BLE (2M PHY, long packets,
  large MTU) are all supported out of the box.
- It leaves room to add MCUboot and over-the-air updates later.
- It builds on Windows with the nRF Connect extension for VS Code.

The code only uses upstream Zephyr APIs, so it builds on plain Zephyr as well as on the
nRF Connect SDK. It has been built with Zephyr v4.1.0 and Zephyr SDK 0.17.0. nRF Connect SDK
v3.0 or newer should work the same way; older versions lack `BT_LE_ADV_OPT_CONN`.

## Layout

| Path | What it does |
|---|---|
| `src/main.c` | Wake, advertising, connection, sleep timers, panel refresh queue |
| `src/ble_image.c` | GATT service: Info, Control, Data characteristics |
| `src/xfer.c` | Transfer state machine: in-order chunks, running CRC-32, resume, commit. Plain C |
| `src/epd.c`, `src/epd_cmds.h` | Panel driver: power switch, reset, init sequence, frame write, refresh |
| `src/battery.c` | Battery voltage (SAADC through the 10M/10M divider), charge status, Battery Service |
| `src/power.c` | Side button with debounce, System OFF with button wake |
| `src/proto.h` | Protocol constants (UUIDs, opcodes, status codes) |
| `boards/openepin/open_e_pin/` | Board definition for the pin (pins from `hardware/README.md`) |
| `boards/nrf52840dk_nrf52840.overlay` | Bench wiring for a DK and a panel adapter board |
| `dts/bindings/` | Devicetree binding for the panel |
| `tests/host/` | Unit tests for `xfer.c` that run on a PC |

## Building

With the nRF Connect SDK (Windows, macOS, Linux): install
[nRF Connect for VS Code](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-VS-Code),
install an SDK and toolchain from it, then **Add build configuration** on this folder and
pick the board `open_e_pin/nrf52840` (or `nrf52840dk/nrf52840` for the DK).

From a terminal with `west` set up:

```
west build -b open_e_pin/nrf52840 firmware
west build -b nrf52840dk/nrf52840 firmware          # bench build
west build -b open_e_pin/nrf52840 firmware -- -DEXTRA_CONF_FILE=debug.conf   # verbose logs
```

The `CMakeLists.txt` adds this folder to `BOARD_ROOT`, so the custom board is found
without copying it into the SDK.

## Flashing and logs

The board has SWD test pads (SWDIO, SWDCLK, RESET, 3V0, GND). Flash with a J-Link or any
CMSIS-DAP probe:

```
west flash                 # nrfjprog / nrfutil with a J-Link
west flash -r pyocd        # CMSIS-DAP probes
```

There is no UART on the board, so logs go to SEGGER RTT. Read them with J-Link RTT Viewer
or `west rtt`. On the DK, logs go to the USB serial port.

## Behaviour

- **Sleep:** System OFF, about 0.4 uA plus the battery divider (about 0.2 uA). Only the
  button wakes it, which reboots the chip.
- **Wake:** the pin advertises as `Open E-Pin` for 60 s. Another press restarts the 60 s.
- **Connected:** stays awake. A connection idle for 2 minutes is dropped.
- **After a disconnect:** keeps advertising for 30 s so an interrupted upload can resume,
  then sleeps.
- **Refresh:** after COMMIT the CRC is checked and the frame is drawn from RAM. The panel
  supply is switched off between refreshes. A refresh is refused below 3.4 V unless USB
  power is present.

Timeouts and thresholds are Kconfig options in [`Kconfig`](Kconfig).

## Tests

```
cd firmware/tests/host
cc -std=c99 -Wall -Wextra -I../../src test_xfer.c ../../src/xfer.c -o test_xfer && ./test_xfer
```

## Before the first power-up of a real panel

1. **Init sequence (`src/epd_cmds.h`)** now follows Good Display's sample for this panel
   (`EPD169_7601`, IST7601 / JD7601): a double reset pulse, the four-byte `INIT_IST7601()`
   test-mode sequence, then DTM1, power on, refresh, power off and deep sleep. The driver
   also waits for BUSY after DTM1 and runs SPI at 2 MHz, both as the sample does. It has
   not been run on a real panel yet.
2. **Colour codes** (`enum epd_color` in `src/epd.h`, `PanelColor` in the app) match the
   sample's values (black 0x0, white 0x1, yellow 0x2, red 0x3, blue 0x5, green 0x6). The
   sample only pushes solid colours and a prebuilt image, so which nibble is the left pixel
   is still to be confirmed on a panel.
3. **BUSY polarity:** low = busy in both the spec's pin table and the vendor sample (note
   6-4 of the spec says the opposite). If the driver times out or never waits, flip
   `GPIO_ACTIVE_LOW` on `busy-gpios`.
4. **Low-frequency clock:** the board uses the internal RC oscillator. If the module turns
   out to have a 32.768 kHz crystal fitted, switch to `CONFIG_CLOCK_CONTROL_NRF_K32SRC_XTAL`.
5. **DC/DC:** the board enables the nRF52840 DC/DC regulator (`reg1`), which needs the
   inductor inside the module. Confirm it on the module datasheet.

## Next steps

- Test the driver on a real panel.
- Add LE Secure Connections bonding so only a paired phone can write images.
- Add MCUboot and BLE firmware updates (SMP).
- Optionally keep the last image in flash so it can be redrawn without the phone.
