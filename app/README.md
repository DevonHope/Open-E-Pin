# Open E-Pin Android app

Kotlin app that finds an Open E-Pin, lets you pick and place an image in the round frame,
converts it to the panel's six colours and uploads it over Bluetooth LE. The protocol is in
[`docs/ble-protocol.md`](../docs/ble-protocol.md).

**Status: framework.** The `core` module (image processing, packing, upload with resume)
has unit tests that pass. The Android UI and BLE code have not been built or run on a phone
yet.

## Modules

| Module | What it does |
|---|---|
| `core` | Plain Kotlin, no Android: palette, dithering, 4-bit packing, protocol encoding, `Uploader` (windowed transfer, NAK rewind, resume, commit) |
| `android` | The app: Jetpack Compose UI, BLE scan and GATT connection, photo picker, round crop, preview |

Keeping the image and protocol logic in `core` means it is tested on a PC, and the same
code could back a desktop or command-line uploader later.

## Image pipeline

1. **Pick** an image with the system photo picker (no storage permission needed).
2. **Place** it in the circle: drag to move, pinch to zoom (`ui/CircleCropper.kt`).
3. **Render** the visible square at 400 x 400 (`image/BitmapPipeline.kt`).
4. **Adjust and dither** (`core/ImageProcessor.kt`): saturation, contrast, rotation, then
   Floyd-Steinberg (photos), Atkinson (crisper) or flat nearest-colour (logos). Colours are
   matched in CIELAB against the six ink colours; everything outside the circle is white.
5. **Pack** to the panel format: two pixels per byte, left pixel in the high nibble.
6. **Upload** with `core/Uploader.kt`: START, data packets of MTU - 7 bytes with at most
   16 KiB in flight, COMMIT, then wait for the pin to finish drawing.

If the link drops, press the pin's button and tap **Retry**: the app reconnects and sends
START with the same image id, and the pin answers with how much it already has.

## Building

Open this `app/` folder in Android Studio (Ladybug or newer) and run the `android`
configuration on a phone with Android 8.0 (API 26) or newer. From a terminal:

```
./gradlew :core:test               # unit tests, no Android SDK needed
./gradlew :android:assembleDebug   # needs the Android SDK
```

## Permissions

- Android 12 and newer: `BLUETOOTH_SCAN` (marked "never for location") and `BLUETOOTH_CONNECT`.
- Android 11 and older: location, which Android requires for BLE scanning there.

## Next steps

- Build and test on a phone against the firmware on a DK.
- Tune the ink colours in `PanelColor` against photos of a real panel.
- Remember the last pin and reconnect to it directly.
- Pairing once the firmware supports bonding.
