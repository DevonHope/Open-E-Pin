# Open E-Pin firmware

Firmware for the Open E-Pin board (Raytac MDBT50Q-1MV2, nRF52840). It sleeps until the side
button is pressed, advertises over Bluetooth LE, receives an image from the Android app,
draws it on the round GDEH0169E02 e-paper panel and goes back to sleep. The BLE protocol
is in [`docs/ble-protocol.md`](../docs/ble-protocol.md).

**Status: framework.** It builds for the pin board and for an nRF52840 DK, and the transfer
logic has unit tests. The panel driver follows Good Display's sample code for this panel, but it has not run on
a real panel yet; see [Checked against the vendor sample](#checked-against-the-vendor-sample).

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

## Checked against the vendor sample

Good Display's sample for this panel (EPD169_7601, Arduino and ESP-IDF, controller
JD7601 / IST7601) was used to verify the driver:

- **Init:** test-mode sequence `FF A5`, `D6 00`, `FF E3`, `E9 01`, copied 1:1 into
  `src/epd_cmds.h`. The controller keeps resolution and waveform in OTP.
- **Reset:** two RST_N low pulses of 20 ms, then wait for BUSY; done twice, as the sample does.
- **Draw:** `10` (then wait for BUSY), 80 000 bytes of frame, `04` power on, `12 00`
  refresh, `02 00` power off, `07 A5` deep sleep, with the sample's delays and timeouts
  (15 s reset, 60 s power, 120 s refresh).
- **BUSY:** the sample waits while BUSY is low, and the board file follows it. The
  specification's note 6-4 says high = busy, so confirm on the first panel: if every wait
  times out or none waits, flip `GPIO_ACTIVE_LOW` on `busy-gpios`.
- **Power-down:** CS, DC and RST are driven low and the SPI pins released before
  `EPD_PWR_EN` goes low, so nothing back-powers the panel.
- **Colour codes and packing:** 0 black, 1 white, 2 yellow, 3 red, 5 blue, 6 green; two
  pixels per byte, left pixel in the high nibble, row-major.
- **SPI:** mode 0 at 2 MHz. The sample raises CS after every byte; this driver sends the
  frame in 4 kB bursts. If the panel shows garbage, set `CONFIG_EPIN_EPD_CS_PER_BYTE=y`.

Still to check on the bench: the panel's orientation (which edge is "up"), and the two
board items below.

1. **Low-frequency clock:** the board uses the internal RC oscillator. If the module turns
   out to have a 32.768 kHz crystal fitted, switch to `CONFIG_CLOCK_CONTROL_NRF_K32SRC_XTAL`.
2. **DC/DC:** the board enables the nRF52840 DC/DC regulator (`reg1`), which needs the
   inductor inside the module. Confirm it on the module datasheet.

## Next steps

- Test on a real panel and fix the orientation if needed.
- Add LE Secure Connections bonding so only a paired phone can write images.
- Add MCUboot and BLE firmware updates (SMP).
- Optionally keep the last image in flash so it can be redrawn without the phone.
