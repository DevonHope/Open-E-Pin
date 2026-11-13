package org.openepin.core

/** The GDEH0169E02 panel: 1.69" round, 400 x 400, six colours (Spectra 6). */
object Panel {
    const val WIDTH = 400
    const val HEIGHT = 400

    /** Format 0x01: 4 bits per pixel, two pixels per byte. */
    const val FRAME_BYTES = WIDTH * HEIGHT / 2
}

/**
 * The panel's colours. [code] is the 4-bit value sent to the panel. [rgb] is roughly what
 * the ink looks like, used as the dithering target. Both come from docs/ble-protocol.md;
 * tune [rgb] against a real panel for better dithering.
 */
enum class PanelColor(val code: Int, val rgb: Int) {
    BLACK(0x0, 0x191E21),
    WHITE(0x1, 0xE8E8E8),
    YELLOW(0x2, 0xEFDE44),
    RED(0x3, 0xB21318),
    BLUE(0x5, 0x2157BA),
    GREEN(0x6, 0x125F20);

    val r: Int get() = (rgb shr 16) and 0xFF
    val g: Int get() = (rgb shr 8) and 0xFF
    val b: Int get() = rgb and 0xFF

    /** Opaque ARGB, for previews. */
    val argb: Int get() = rgb or (0xFF shl 24)

    companion object {
        fun fromCode(code: Int): PanelColor =
            entries.firstOrNull { it.code == code } ?: error("Invalid colour code $code")
    }
}
