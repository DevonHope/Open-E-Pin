package org.openepin.core

import kotlin.math.max
import kotlin.math.min

enum class DitherMethod {
    /** Nearest colour, no dithering. Good for logos and flat art. */
    NONE,

    /** Floyd-Steinberg error diffusion. Good default for photos. */
    FLOYD_STEINBERG,

    /** Atkinson: diffuses only 3/4 of the error. More contrast, less noise. */
    ATKINSON,
}

data class ProcessOptions(
    val dither: DitherMethod = DitherMethod.FLOYD_STEINBERG,
    /** Scan alternate rows right to left, which avoids diagonal "worm" patterns. */
    val serpentine: Boolean = true,
    /** 1.0 = unchanged. The inks are muted, so a little extra saturation usually helps. */
    val saturation: Float = 1.2f,
    /** 1.0 = unchanged. */
    val contrast: Float = 1.0f,
    /** -1..1, 0 = unchanged. */
    val brightness: Float = 0f,
    /** Clockwise rotation in degrees (0, 90, 180, 270), to match how the panel is mounted. */
    val rotation: Int = 0,
    /** Paint everything outside the round visible area white. */
    val maskCircle: Boolean = true,
)

/**
 * The result of processing: one [PanelColor] per pixel, row-major, [Panel.WIDTH] x [Panel.HEIGHT].
 */
class PanelImage(val pixels: Array<PanelColor>) {
    init {
        require(pixels.size == Panel.WIDTH * Panel.HEIGHT) { "Expected ${Panel.WIDTH}x${Panel.HEIGHT} pixels" }
    }

    /**
     * Packs to format 0x01: row-major, two pixels per byte, left pixel in the high nibble.
     */
    fun pack(): ByteArray {
        val out = ByteArray(Panel.FRAME_BYTES)
        for (i in out.indices) {
            val hi = pixels[2 * i].code
            val lo = pixels[2 * i + 1].code
            out[i] = ((hi shl 4) or lo).toByte()
        }
        return out
    }

    /** ARGB preview of what the panel will show (approximately). */
    fun previewArgb(): IntArray = IntArray(pixels.size) { pixels[it].argb }

    companion object {
        fun unpack(frame: ByteArray): PanelImage {
            require(frame.size == Panel.FRAME_BYTES)
            val px = Array(Panel.WIDTH * Panel.HEIGHT) { i ->
                val b = frame[i / 2].toInt() and 0xFF
                PanelColor.fromCode(if (i % 2 == 0) b shr 4 else b and 0x0F)
            }
            return PanelImage(px)
        }
    }
}

/**
 * Turns an image into panel colours. Pure Kotlin so it runs (and is tested) on the JVM;
 * the Android app feeds it pixels from a Bitmap.
 */
object ImageProcessor {
    private val palette = PanelColor.entries.toTypedArray()

    /**
     * @param argb [Panel.WIDTH] x [Panel.HEIGHT] pixels, row-major ARGB (as Bitmap.getPixels gives).
     *   Crop and scale to 400 x 400 first, e.g. with [resize].
     */
    fun process(argb: IntArray, options: ProcessOptions = ProcessOptions()): PanelImage {
        val w = Panel.WIDTH
        val h = Panel.HEIGHT
        require(argb.size == w * h) { "Expected ${w}x$h pixels, got ${argb.size}" }

        val rotated = rotate(argb, w, h, options.rotation)

        // Working buffer in float RGB, 0..255, after tone adjustments.
        val r = FloatArray(w * h)
        val g = FloatArray(w * h)
        val b = FloatArray(w * h)
        for (i in rotated.indices) {
            val c = rotated[i]
            val a = ((c ushr 24) and 0xFF) / 255f
            // Composite over white so transparent areas come out white.
            var cr = ((c shr 16) and 0xFF) * a + 255f * (1 - a)
            var cg = ((c shr 8) and 0xFF) * a + 255f * (1 - a)
            var cb = (c and 0xFF) * a + 255f * (1 - a)

            // Brightness and contrast around mid-grey.
            val bOff = options.brightness * 255f
            cr = (cr - 128f) * options.contrast + 128f + bOff
            cg = (cg - 128f) * options.contrast + 128f + bOff
            cb = (cb - 128f) * options.contrast + 128f + bOff

            // Saturation around luma.
            val luma = 0.299f * cr + 0.587f * cg + 0.114f * cb
            cr = luma + (cr - luma) * options.saturation
            cg = luma + (cg - luma) * options.saturation
            cb = luma + (cb - luma) * options.saturation

            r[i] = cr.coerceIn(0f, 255f)
            g[i] = cg.coerceIn(0f, 255f)
            b[i] = cb.coerceIn(0f, 255f)
        }

        val inside = BooleanArray(w * h) { true }
        if (options.maskCircle) {
            val cx = (w - 1) / 2f
            val cy = (h - 1) / 2f
            val rad = min(w, h) / 2f
            for (y in 0 until h) for (x in 0 until w) {
                val dx = x - cx
                val dy = y - cy
                if (dx * dx + dy * dy > rad * rad) {
                    val i = y * w + x
                    inside[i] = false
                    r[i] = 255f; g[i] = 255f; b[i] = 255f
                }
            }
        }

        val out = Array(w * h) { PanelColor.WHITE }
        val kernel = when (options.dither) {
            DitherMethod.NONE -> emptyList()
            DitherMethod.FLOYD_STEINBERG -> FLOYD_STEINBERG
            DitherMethod.ATKINSON -> ATKINSON
        }

        for (y in 0 until h) {
            val reverse = options.serpentine && y % 2 == 1
            for (step in 0 until w) {
                val x = if (reverse) w - 1 - step else step
                val i = y * w + x
                if (!inside[i]) {
                    out[i] = PanelColor.WHITE
                    continue
                }
                // Clamp before matching so accumulated error can't run away
                // (pure black is darker than the black ink, for example).
                val pr = r[i].coerceIn(0f, 255f)
                val pg = g[i].coerceIn(0f, 255f)
                val pb = b[i].coerceIn(0f, 255f)
                val c = nearest(pr, pg, pb)
                out[i] = c
                if (kernel.isEmpty()) continue
                val er = pr - c.r
                val eg = pg - c.g
                val eb = pb - c.b
                for (k in kernel) {
                    val nx = if (reverse) x - k.dx else x + k.dx
                    val ny = y + k.dy
                    if (nx < 0 || nx >= w || ny >= h) continue
                    val j = ny * w + nx
                    if (!inside[j]) continue
                    r[j] += er * k.weight
                    g[j] += eg * k.weight
                    b[j] += eb * k.weight
                }
            }
        }
        return PanelImage(out)
    }

    /**
     * Closest palette colour by distance in CIELAB, which tracks perceived difference far
     * better than RGB distance (in RGB, mid-grey is "closest" to the blue ink).
     */
    fun nearest(r: Float, g: Float, b: Float): PanelColor {
        val lab = FloatArray(3)
        srgbToLab(r, g, b, lab)
        var best = palette[0]
        var bestD = Float.MAX_VALUE
        for (k in palette.indices) {
            val p = paletteLab[k]
            val dl = lab[0] - p[0]
            val da = lab[1] - p[1]
            val db = lab[2] - p[2]
            val d = dl * dl + da * da + db * db
            if (d < bestD) {
                bestD = d
                best = palette[k]
            }
        }
        return best
    }

    private val paletteLab: Array<FloatArray> = Array(palette.size) { k ->
        FloatArray(3).also { srgbToLab(palette[k].r.toFloat(), palette[k].g.toFloat(), palette[k].b.toFloat(), it) }
    }

    /** sRGB 0..255 to CIELAB (D65). */
    internal fun srgbToLab(r: Float, g: Float, b: Float, out: FloatArray) {
        fun lin(c: Float): Double {
            val v = c / 255.0
            return if (v <= 0.04045) v / 12.92 else Math.pow((v + 0.055) / 1.055, 2.4)
        }
        val lr = lin(r); val lg = lin(g); val lb = lin(b)
        val x = (0.4124 * lr + 0.3576 * lg + 0.1805 * lb) / 0.95047
        val y = 0.2126 * lr + 0.7152 * lg + 0.0722 * lb
        val z = (0.0193 * lr + 0.1192 * lg + 0.9505 * lb) / 1.08883
        fun f(t: Double) = if (t > 216.0 / 24389.0) Math.cbrt(t) else (24389.0 / 27.0 * t + 16.0) / 116.0
        val fx = f(x); val fy = f(y); val fz = f(z)
        out[0] = (116.0 * fy - 16.0).toFloat()
        out[1] = (500.0 * (fx - fy)).toFloat()
        out[2] = (200.0 * (fy - fz)).toFloat()
    }

    /** Rotates a square ARGB image clockwise by 0, 90, 180 or 270 degrees. */
    fun rotate(argb: IntArray, w: Int, h: Int, degrees: Int): IntArray {
        val d = ((degrees % 360) + 360) % 360
        require(d % 90 == 0) { "Rotation must be a multiple of 90" }
        if (d == 0) return argb
        require(w == h) { "Rotation needs a square image" }
        val n = w
        val out = IntArray(n * n)
        for (y in 0 until n) for (x in 0 until n) {
            val src = argb[y * n + x]
            val (nx, ny) = when (d) {
                90 -> Pair(n - 1 - y, x)
                180 -> Pair(n - 1 - x, n - 1 - y)
                else -> Pair(y, n - 1 - x)
            }
            out[ny * n + nx] = src
        }
        return out
    }

    /**
     * Centre-crops to a square and scales to [size] x [size] with area averaging. The app
     * normally does this with the crop UI; this is for tests and tools.
     */
    fun resize(argb: IntArray, w: Int, h: Int, size: Int = Panel.WIDTH): IntArray {
        val side = min(w, h)
        val x0 = (w - side) / 2
        val y0 = (h - side) / 2
        val out = IntArray(size * size)
        val scale = side.toFloat() / size
        for (oy in 0 until size) for (ox in 0 until size) {
            val sx0 = x0 + (ox * scale).toInt()
            val sy0 = y0 + (oy * scale).toInt()
            val sx1 = max(sx0 + 1, x0 + ((ox + 1) * scale).toInt())
            val sy1 = max(sy0 + 1, y0 + ((oy + 1) * scale).toInt())
            var a = 0L; var rr = 0L; var gg = 0L; var bb = 0L; var n = 0
            for (sy in sy0 until min(sy1, h)) for (sx in sx0 until min(sx1, w)) {
                val c = argb[sy * w + sx]
                a += (c ushr 24) and 0xFF; rr += (c shr 16) and 0xFF
                gg += (c shr 8) and 0xFF; bb += c and 0xFF; n++
            }
            out[oy * size + ox] = if (n == 0) 0 else
                ((a / n).toInt() shl 24) or ((rr / n).toInt() shl 16) or ((gg / n).toInt() shl 8) or (bb / n).toInt()
        }
        return out
    }

    private class Tap(val dx: Int, val dy: Int, val weight: Float)

    private val FLOYD_STEINBERG = listOf(
        Tap(1, 0, 7 / 16f), Tap(-1, 1, 3 / 16f), Tap(0, 1, 5 / 16f), Tap(1, 1, 1 / 16f),
    )

    private val ATKINSON = listOf(
        Tap(1, 0, 1 / 8f), Tap(2, 0, 1 / 8f), Tap(-1, 1, 1 / 8f),
        Tap(0, 1, 1 / 8f), Tap(1, 1, 1 / 8f), Tap(0, 2, 1 / 8f),
    )
}
