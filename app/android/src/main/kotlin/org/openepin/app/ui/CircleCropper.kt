package org.openepin.app.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import org.openepin.app.image.BitmapPipeline
import org.openepin.app.image.CropState

/**
 * Square view with a round window the size of the panel. Drag to move the image, pinch to
 * zoom. Everything outside the circle is dimmed, since the panel won't show it.
 */
@Composable
fun CircleCropper(
    image: ImageBitmap,
    crop: CropState,
    onCropChange: (CropState) -> Unit,
    modifier: Modifier = Modifier,
) {
    val current by rememberUpdatedState(crop)
    val onChange by rememberUpdatedState(onCropChange)

    Canvas(
        modifier
            .aspectRatio(1f)
            .clipToBounds()
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoom, _ ->
                    val side = size.width.toFloat()
                    onChange(
                        current.copy(
                            scale = (current.scale * zoom).coerceIn(0.5f, 8f),
                            offsetX = current.offsetX + pan.x / side,
                            offsetY = current.offsetY + pan.y / side,
                        ),
                    )
                }
            },
    ) {
        val side = size.width
        val k = BitmapPipeline.coverScale(image.width, image.height, side) * crop.scale

        drawRect(Color.White)
        withTransform({
            translate(side / 2 + crop.offsetX * side, side / 2 + crop.offsetY * side)
            scale(k, k, pivot = Offset.Zero)
            translate(-image.width / 2f, -image.height / 2f)
        }) {
            drawImage(image)
        }

        val outside = Path().apply {
            fillType = PathFillType.EvenOdd
            addRect(Rect(0f, 0f, side, side))
            addOval(Rect(0f, 0f, side, side))
        }
        drawPath(outside, Color.Black.copy(alpha = 0.55f))
        drawCircle(Color.White, radius = side / 2 - 1.dp.toPx(), style = Stroke(width = 2.dp.toPx()))
    }
}
