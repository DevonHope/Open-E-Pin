package org.openepin.core

import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout

/**
 * The transport the uploader needs. The Android app implements it over BluetoothGatt;
 * tests implement it with a simulated pin.
 */
interface PinLink {
    /** ATT MTU agreed with the pin (23 until the MTU exchange). */
    val mtu: Int

    /** Control characteristic notifications, raw. Hot: only values after collection starts. */
    val notifications: Flow<ByteArray>

    /** Write with response to the Control characteristic. */
    suspend fun writeControl(value: ByteArray)

    /** Write without response to the Data characteristic. Suspends while the stack is busy. */
    suspend fun writeData(value: ByteArray)
}

data class UploadProgress(val sent: Int, val acknowledged: Int, val total: Int) {
    val fraction: Float get() = if (total == 0) 0f else acknowledged.toFloat() / total
}

data class UploadConfig(
    val windowBytes: Int = Protocol.WINDOW_BYTES,
    val responseTimeoutMs: Long = 5_000,
    val stallTimeoutMs: Long = 5_000,
    val refreshTimeoutMs: Long = 90_000,
    val maxStalls: Int = 5,
)

/**
 * Sends one packed image to the pin: START (or resume), windowed data packets, COMMIT,
 * then waits for the panel to finish. See docs/ble-protocol.md.
 *
 * To resume after a dropped link, reconnect and call [upload] again with the same
 * [imageId]: the pin answers START with the offset it already has.
 */
class Uploader(private val link: PinLink, private val config: UploadConfig = UploadConfig()) {

    suspend fun upload(
        image: ByteArray,
        imageId: Int,
        format: Int = Protocol.FORMAT_4BPP,
        waitForRefresh: Boolean = true,
        onProgress: (UploadProgress) -> Unit = {},
    ) = coroutineScope {
        val events = Channel<PinEvent>(Channel.UNLIMITED)
        val collector = launch(start = CoroutineStart.UNDISPATCHED) {
            link.notifications.collect { events.send(Protocol.parseEvent(it)) }
        }
        try {
            run(events, image, imageId, format, waitForRefresh, onProgress)
        } finally {
            collector.cancel()
        }
    }

    private suspend fun run(
        events: Channel<PinEvent>,
        image: ByteArray,
        imageId: Int,
        format: Int,
        waitForRefresh: Boolean,
        onProgress: (UploadProgress) -> Unit,
    ) {
        val total = image.size
        val crc = Protocol.crc32(image)

        link.writeControl(Protocol.start(format, total, crc, imageId))
        val start = awaitResponse(events, Protocol.OP_START)
        start.status.orThrow("START")
        var acked = start.u32.coerceIn(0, total)
        var next = acked
        onProgress(UploadProgress(next, acked, total))

        val payload = (link.mtu - Protocol.ATT_HEADER - Protocol.DATA_HEADER).coerceAtLeast(16)
        var stalls = 0

        while (acked < total) {
            // Fill the window.
            while (next < total && next - acked < config.windowBytes) {
                val n = minOf(payload, total - next)
                link.writeData(Protocol.dataPacket(next, image, n))
                next += n
                onProgress(UploadProgress(next, acked, total))
            }

            // Wait for the pin to catch up.
            val ev = try {
                withTimeout(config.stallTimeoutMs) { events.receive() }
            } catch (e: TimeoutCancellationException) {
                if (++stalls > config.maxStalls) throw e
                // Ask where it is and carry on from there.
                link.writeControl(Protocol.status())
                val st = awaitResponse(events, Protocol.OP_STATUS)
                val offset = java.nio.ByteBuffer.wrap(st.payload, 1, 4)
                    .order(java.nio.ByteOrder.LITTLE_ENDIAN).int
                acked = offset; next = offset
                continue
            }
            when (ev) {
                is PinEvent.Progress -> {
                    acked = maxOf(acked, ev.offset.coerceAtMost(total))
                    stalls = 0
                }
                is PinEvent.Nak -> {
                    acked = ev.expectedOffset.coerceIn(0, total)
                    next = acked
                }
                else -> Unit
            }
            onProgress(UploadProgress(next, acked, total))
        }

        link.writeControl(Protocol.commit())
        awaitResponse(events, Protocol.OP_COMMIT).status.orThrow("COMMIT")

        if (waitForRefresh) {
            val done = withTimeout(config.refreshTimeoutMs) {
                var e: PinEvent
                do { e = events.receive() } while (e !is PinEvent.RefreshDone)
                e as PinEvent.RefreshDone
            }
            done.status.orThrow("Refresh")
        }
    }

    private suspend fun awaitResponse(events: Channel<PinEvent>, op: Int): PinEvent.Response =
        withTimeout(config.responseTimeoutMs) {
            var r: PinEvent.Response? = null
            while (r == null) {
                val e = events.receive()
                if (e is PinEvent.Response && e.op == op) r = e
            }
            r
        }

    private fun Status.orThrow(what: String) {
        if (this != Status.OK) throw PinException(this, "$what failed")
    }
}
