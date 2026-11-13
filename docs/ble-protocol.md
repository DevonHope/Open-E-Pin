# Open E-Pin BLE protocol

Version 1. This is the contract between the firmware in [`firmware/`](../firmware) and the
Android app in [`app/`](../app). Change it here first, then in both places, and bump the
protocol version when an old app could misread a new pin (or the other way round).

All multi-byte fields are **little endian**. Lengths are in bytes.

## Connection lifecycle

1. The pin sleeps (nRF52840 System OFF) and does **not** advertise.
2. A press on the side button wakes it. It advertises as connectable for 60 s
   (`CONFIG_EPIN_ADV_TIMEOUT_S`) with the name `Open E-Pin` and the image service UUID in the
   scan response.
3. The app connects, asks for a 247-byte ATT MTU, 2M PHY and a short connection interval,
   then enables notifications on the Control characteristic.
4. The app uploads an image and commits it. The pin redraws the panel and reports when it
   is done.
5. After the app disconnects, the pin keeps advertising for 30 s
   (`CONFIG_EPIN_IDLE_TIMEOUT_S`) so a dropped link can resume, then goes back to sleep.
   Pressing the button while awake restarts the 60 s window.

A partly received image stays in RAM until the pin sleeps, so an upload interrupted by a
dropped link can resume where it stopped. Sleeping clears it.

## GATT layout

| Service / characteristic | UUID | Properties |
|---|---|---|
| Image service | `7a1e0001-3c4d-4b5e-9f60-0e9e0e9e0e9e` | primary |
| Info | `7a1e0002-3c4d-4b5e-9f60-0e9e0e9e0e9e` | read |
| Control | `7a1e0003-3c4d-4b5e-9f60-0e9e0e9e0e9e` | write (with response), notify |
| Data | `7a1e0004-3c4d-4b5e-9f60-0e9e0e9e0e9e` | write without response |
| Battery Service (standard) | `0x180F` / Battery Level `0x2A19` | read, notify |
| Device Information (standard) | `0x180A` | read |

## Image format

Only one format exists in version 1.

**Format `0x01`, 4 bits per pixel, panel colour codes.** 400 x 400 pixels, row-major from
the top-left corner as seen from the front, two pixels per byte, **the left pixel in the high
nibble**. Total size 80 000 bytes. Pixel values are the panel's colour codes:

| Code | Colour | sRGB used for dithering (approximate, tune on a real panel) |
|---|---|---|
| `0x0` | Black | `#191E21` |
| `0x1` | White | `#E8E8E8` |
| `0x2` | Yellow | `#EFDE44` |
| `0x3` | Red | `#B21318` |
| `0x5` | Blue | `#2157BA` |
| `0x6` | Green | `#125F20` |

Codes `0x4` and `0x7` to `0xF` are invalid. The panel is round: pixels outside the circle
of radius 200 centred on the image are not visible, and the app sends them as white.

The codes, the packing (row-major, left pixel in the high nibble) and the 80 000-byte
frame match Good Display's sample code for this panel (EPD169_7601); its example image only
renders correctly when unpacked this way.

## Info characteristic (read, 16 bytes)

| Offset | Size | Field |
|---|---|---|
| 0 | 1 | Protocol version, `1` |
| 1 | 1 | Hardware revision, `1` for board v0.1 |
| 2 | 2 | Width in pixels, `400` |
| 4 | 2 | Height in pixels, `400` |
| 6 | 1 | Supported formats, bit mask: bit 0 = format `0x01` |
| 7 | 1 | Transfer state (see below) |
| 8 | 2 | Battery voltage in mV |
| 10 | 1 | Battery level in percent (0 to 100) |
| 11 | 1 | Flags: bit 0 = charging, bit 1 = USB power present |
| 12 | 3 | Firmware version: major, minor, patch |
| 15 | 1 | Reserved, `0` |

Transfer states: `0` idle, `1` receiving, `2` received and verified, `3` refreshing the panel.

## Control characteristic

The app writes requests (write with response). The pin answers each request with a
notification whose first byte is the request opcode with the top bit set, followed by a
status byte. The pin also sends unsolicited events.

### Requests (app to pin)

| Opcode | Name | Payload | Response payload (after opcode and status) |
|---|---|---|---|
| `0x01` | START | format u8, length u32, CRC-32 u32, image id u32 (13 bytes) | offset u32: where to continue sending |
| `0x02` | STATUS | none | state u8, offset u32 |
| `0x03` | COMMIT | none | none. A REFRESH_DONE event follows later |
| `0x04` | ABORT | none | none |
| `0x05` | CLEAR | colour code u8 | none. Fills the panel with one colour; REFRESH_DONE follows |
| `0x06` | SLEEP | none | none. The pin disconnects and sleeps |

**START** begins a transfer, or resumes one. The image id is any 32-bit number the app
picks for this image. If the pin already holds a partial or complete transfer with the
same format, length, CRC and id, it answers with the number of bytes it already has, and
the app continues from there. Otherwise it discards what it had and answers with offset 0.

**CRC-32** is the standard IEEE 802.3 / zlib CRC (polynomial `0xEDB88320` reflected, initial
value and final XOR `0xFFFFFFFF`) over the whole image, the same as `java.util.zip.CRC32`.

### Responses and events (pin to app, notifications)

| First byte | Name | Payload |
|---|---|---|
| `0x81` to `0x86` | Response to request `0x01` to `0x06` | status u8, then as listed above |
| `0x90` | PROGRESS | offset u32: bytes received so far, in order |
| `0x91` | NAK | expected offset u32: a data packet arrived out of order; resend from here |
| `0xA0` | REFRESH_DONE | status u8 |

The pin sends PROGRESS every 4096 bytes and once more when the last byte arrives. It sends
at most one NAK until a packet at the expected offset arrives.

### Status codes

| Code | Name | Meaning |
|---|---|---|
| `0` | OK | |
| `1` | BAD_LENGTH | Wrong image length for the format |
| `2` | BAD_STATE | Request not valid now (for example COMMIT before all bytes arrived) |
| `3` | CRC_MISMATCH | Image CRC does not match. The pin drops the transfer |
| `4` | BAD_FORMAT | Format not supported |
| `5` | BUSY | The panel is refreshing. Try again after REFRESH_DONE |
| `6` | BAD_OFFSET | Data packet offset is not the expected one |
| `7` | LOW_BATTERY | Battery below `CONFIG_EPIN_MIN_REFRESH_MV`; refresh refused |
| `8` | PANEL_ERROR | Panel did not finish (BUSY timeout) |
| `9` | UNKNOWN_OPCODE | |

## Data characteristic

Each write without response carries one packet:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Offset of the first payload byte within the image, u32 |
| 4 | n | Image bytes, `n` up to ATT MTU minus 7 (240 with a 247-byte MTU) |

The pin accepts a packet only when its offset equals the number of bytes it already has.
A packet that would run past the end of the image is dropped.

## Flow control

Write without response has no acknowledgement, so the app keeps at most **16 KiB** in
flight beyond the last PROGRESS offset, and waits for the next PROGRESS before sending more.
On a NAK it rewinds to the expected offset. If no event arrives for 5 s it sends STATUS and
continues from the offset in the answer.

## Typical upload

```
app                                       pin
 | write Control  01 01 80380100 crc id    |
 |<------------ notify 81 00 00000000      |   start at offset 0
 | write Data  00000000 [240 bytes]        |
 | write Data  f0000000 [240 bytes]  ...   |
 |<------------ notify 90 00100000         |   PROGRESS 4096
 |                ...                      |
 |<------------ notify 90 80380100         |   PROGRESS 80000 (all bytes)
 | write Control  03                       |
 |<------------ notify 83 00               |   CRC ok, refresh started
 |<------------ notify a0 00               |   about 20 s later: panel done
```

## Security

Version 1 has no pairing. The pin only advertises for a minute after a button press, which
limits who can write to it. Adding LE Secure Connections bonding is a planned follow-up.
