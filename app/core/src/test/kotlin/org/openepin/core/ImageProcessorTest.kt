package org.openepin.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ImageProcessorTest {
    private val n = Panel.WIDTH * Panel.HEIGHT

    private fun solid(argb: Int) = IntArray(n) { argb }

    @Test
    fun packsLeftPixelInHighNibble() {
        val px = Array(n) { PanelColor.WHITE }
        px[0] = PanelColor.RED   // 0x3
        px[1] = PanelColor.BLUE  // 0x5
        val packed = PanelImage(px).pack()
        assertEquals(Panel.FRAME_BYTES, packed.size)
        assertEquals(0x35, packed[0].toInt() and 0xFF)
        assertEquals(0x11, packed[1].toInt() and 0xFF)
        assertEquals(PanelColor.RED, PanelImage.unpack(packed).pixels[0])
    }

    @Test
    fun solidFramesMatchVendorColourBytes() {
        // COLOR_BLACK..COLOR_GREEN in Good Display's EPD169_7601 sample.
        val vendor = mapOf(
            PanelColor.BLACK to 0x00, PanelColor.WHITE to 0x11, PanelColor.YELLOW to 0x22,
            PanelColor.RED to 0x33, PanelColor.BLUE to 0x55, PanelColor.GREEN to 0x66,
        )
        for ((c, byte) in vendor) {
            val packed = PanelImage(Array(n) { c }).pack()
            assertTrue("$c", packed.all { (it.toInt() and 0xFF) == byte })
        }
    }

    @Test
    fun paletteColoursMapToThemselves() {
        for (c in PanelColor.entries) {
            val img = ImageProcessor.process(
                solid(c.argb),
                ProcessOptions(saturation = 1f, maskCircle = false),
            )
            assertTrue("$c", img.pixels.all { it == c })
        }
    }

    @Test
    fun outsideCircleIsWhite() {
        val img = ImageProcessor.process(solid(0xFF000000.toInt()))
        assertEquals(PanelColor.WHITE, img.pixels[0])                    // corner
        assertEquals(PanelColor.WHITE, img.pixels[n - 1])
        assertEquals(PanelColor.BLACK, img.pixels[200 * Panel.WIDTH + 200]) // centre
    }

    @Test
    fun ditheringMixesGrey() {
        val grey = 0xFF808080.toInt()
        val img = ImageProcessor.process(solid(grey), ProcessOptions(maskCircle = false, saturation = 1f))
        val blacks = img.pixels.count { it == PanelColor.BLACK }
        val whites = img.pixels.count { it == PanelColor.WHITE }
        // Mostly a black/white mix, roughly balanced.
        assertTrue(blacks + whites > n * 0.9)
        assertTrue(blacks > n * 0.3 && whites > n * 0.3)

        val flat = ImageProcessor.process(solid(grey), ProcessOptions(dither = DitherMethod.NONE, maskCircle = false))
        assertEquals(1, flat.pixels.toSet().size)
    }

    @Test
    fun rotatesClockwise() {
        val src = IntArray(n)
        src[0] = 7 // top-left
        val r = ImageProcessor.rotate(src, Panel.WIDTH, Panel.HEIGHT, 90)
        assertEquals(7, r[Panel.WIDTH - 1]) // top-right
    }

    @Test
    fun resizesToPanel() {
        val big = IntArray(1200 * 800) { 0xFFFF0000.toInt() }
        val out = ImageProcessor.resize(big, 1200, 800)
        assertEquals(n, out.size)
        assertEquals(0xFFFF0000.toInt(), out[n / 2])
    }

    @Test
    fun protocolCrcMatchesFirmwareCheckValue() {
        assertEquals(0xCBF43926L, Protocol.crc32("123456789".toByteArray()))
    }

    @Test
    fun parsesInfo() {
        val raw = byteArrayOf(1, 1, 0x90.toByte(), 1, 0x90.toByte(), 1, 1, 0, 0x68, 0x10, 80, 1, 0, 1, 0, 0)
        val info = PinInfo.parse(raw)
        assertEquals(400, info.width)
        assertEquals(4200, info.batteryMillivolts)
        assertEquals(80, info.batteryPercent)
        assertTrue(info.charging)
        assertEquals("0.1.0", info.firmwareVersion)
        assertTrue(info.supports(Protocol.FORMAT_4BPP))
    }
}
