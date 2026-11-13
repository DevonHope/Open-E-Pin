package org.openepin.app.image

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.ImageDecoder
import android.graphics.Paint
import android.net.Uri
import android.os.Build
import org.openepin.core.Panel
import org.openepin.core.PanelImage
import kotlin.math.max

/**
 * Where the user placed the image inside the round crop. [offsetX] and [offsetY] are in
 * units of the crop circle's diameter, so the same state works at any size: on screen,
 * and when rendering the 400 x 400 output.
 */
data class CropState(
    val scale: Float = 1f,
    val offsetX: Float = 0f,
    val offsetY: Float = 0f,
)

object BitmapPipeline {

    /** Decodes a picked image as a software ARGB_8888 bitmap no larger than [maxSide]. */
    fun decode(context: Context, uri: Uri, maxSide: Int = 2048): Bitmap {
        if (Build.VERSION.SDK_INT >= 28) {
            val src = ImageDecoder.createSource(context.contentResolver, uri)
            return ImageDecoder.decodeBitmap(src) { decoder, info, _ ->
                decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
                val w = info.size.width
                val h = info.size.height
                val f = max(w, h).toFloat() / maxSide
                if (f > 1f) decoder.setTargetSize((w / f).toInt(), (h / f).toInt())
            }.copy(Bitmap.Config.ARGB_8888, false)
        }
        // Android 8: BitmapFactory. Ignores EXIF rotation.
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        context.contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, bounds) }
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / (sample * 2) >= maxSide) sample *= 2
        val opts = BitmapFactory.Options().apply {
            inSampleSize = sample
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        return context.contentResolver.openInputStream(uri).use { BitmapFactory.decodeStream(it, null, opts) }
            ?: error("Could not decode image")
    }

    /** Scale that makes the image just cover a square of side [side]. */
    fun coverScale(bitmapWidth: Int, bitmapHeight: Int, side: Float): Float =
        max(side / bitmapWidth, side / bitmapHeight)

    /**
     * Renders the cropped square at [size] x [size], white behind the image. Uses the same
     * transform as the on-screen cropper.
     */
    fun renderCrop(src: Bitmap, crop: CropState, size: Int = Panel.WIDTH): Bitmap {
        val out = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(out)
        canvas.drawColor(Color.WHITE)
        val s = size.toFloat()
        canvas.translate(s / 2 + crop.offsetX * s, s / 2 + crop.offsetY * s)
        val k = coverScale(src.width, src.height, s) * crop.scale
        canvas.scale(k, k)
        canvas.translate(-src.width / 2f, -src.height / 2f)
        canvas.drawBitmap(src, 0f, 0f, Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG))
        return out
    }

    fun pixels(bitmap: Bitmap): IntArray {
        val px = IntArray(bitmap.width * bitmap.height)
        bitmap.getPixels(px, 0, bitmap.width, 0, 0, bitmap.width, bitmap.height)
        return px
    }

    /** What the panel will roughly look like. */
    fun preview(image: PanelImage): Bitmap =
        Bitmap.createBitmap(image.previewArgb(), Panel.WIDTH, Panel.HEIGHT, Bitmap.Config.ARGB_8888)
}
