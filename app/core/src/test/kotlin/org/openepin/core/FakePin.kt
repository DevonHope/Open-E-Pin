package org.openepin.core

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.zip.CRC32

/**
 * A simulated pin that follows docs/ble-protocol.md, mirroring firmware/src/xfer.c.
 * State survives across [link] objects, like the pin's RAM across a reconnect.
 */
class FakePin {
    var frame = ByteArray(Panel.FRAME_BYTES)
    var state = TransferState.IDLE
    var offset = 0
    var refreshed: ByteArray? = null
    private var len = 0
    private var crcExpected = 0
    private var id = 0
    private var crc = CRC32()
    private var lastAck = 0
    private var nakSent = false

    /** Drop the data packet with this offset once (simulates a lost packet). */
    var dropOnceAtOffset: Int? = null

    /** Fail the link after this many data packets (simulates a disconnect). */
    var disconnectAfterPackets: Int? = null

    /** Corrupt the first byte received (CRC mismatch test). */
    var corrupt = false

    fun link(mtu: Int = 247) = Link(mtu)

    inner class Link(override val mtu: Int) : PinLink {
        private val flow = MutableSharedFlow<ByteArray>(extraBufferCapacity = 1024)
        override val notifications: SharedFlow<ByteArray> = flow
        private var packets = 0
        var connected = true

        private fun notify(vararg bytes: Byte) = check(flow.tryEmit(bytes))

        private fun respond(op: Int, status: Status, payload: ByteArray = ByteArray(0)) =
            notify(*(byteArrayOf((0x80 or op).toByte(), status.code.toByte()) + payload))

        private fun u32(v: Int) = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(v).array()

        override suspend fun writeControl(value: ByteArray) {
            if (!connected) throw IOException("disconnected")
            val b = ByteBuffer.wrap(value).order(ByteOrder.LITTLE_ENDIAN)
            when (value[0].toInt()) {
                Protocol.OP_START -> {
                    val fmt = value[1].toInt()
                    val l = b.getInt(2); val c = b.getInt(6); val i = b.getInt(10)
                    if (fmt != Protocol.FORMAT_4BPP) return respond(Protocol.OP_START, Status.BAD_FORMAT, u32(0))
                    if (l != Panel.FRAME_BYTES) return respond(Protocol.OP_START, Status.BAD_LENGTH, u32(0))
                    if (state == TransferState.RECEIVING && l == len && c == crcExpected && i == id) {
                        nakSent = false; lastAck = offset
                    } else {
                        state = TransferState.RECEIVING; len = l; crcExpected = c; id = i
                        offset = 0; crc = CRC32(); lastAck = 0; nakSent = false
                    }
                    respond(Protocol.OP_START, Status.OK, u32(offset))
                }
                Protocol.OP_STATUS -> respond(
                    Protocol.OP_STATUS, Status.OK, byteArrayOf(state.ordinal.toByte()) + u32(offset),
                )
                Protocol.OP_COMMIT -> {
                    if (state != TransferState.RECEIVING || offset != len) {
                        return respond(Protocol.OP_COMMIT, Status.BAD_STATE)
                    }
                    if (crc.value.toInt() != crcExpected) {
                        state = TransferState.IDLE
                        return respond(Protocol.OP_COMMIT, Status.CRC_MISMATCH)
                    }
                    respond(Protocol.OP_COMMIT, Status.OK)
                    refreshed = frame.copyOf()
                    state = TransferState.IDLE
                    notify(Protocol.EVT_REFRESH_DONE.toByte(), 0)
                }
                else -> respond(value[0].toInt(), Status.UNKNOWN_OPCODE)
            }
        }

        override suspend fun writeData(value: ByteArray) {
            if (!connected) throw IOException("disconnected")
            disconnectAfterPackets?.let {
                if (packets >= it) { connected = false; throw IOException("link lost") }
            }
            packets++
            val off = ByteBuffer.wrap(value).order(ByteOrder.LITTLE_ENDIAN).getInt(0)
            if (dropOnceAtOffset == off) { dropOnceAtOffset = null; return }
            if (state != TransferState.RECEIVING) return
            if (off != offset) {
                if (!nakSent) { nakSent = true; notify(*(byteArrayOf(0x91.toByte()) + u32(offset))) }
                return
            }
            val n = value.size - 4
            System.arraycopy(value, 4, frame, off, n)
            if (corrupt && off == 0) { frame[0] = (frame[0].toInt() xor 0xFF).toByte(); corrupt = false }
            crc.update(frame, off, n)
            offset += n; nakSent = false
            if (offset == len || offset - lastAck >= 4096) {
                lastAck = offset
                notify(*(byteArrayOf(0x90.toByte()) + u32(offset)))
            }
        }
    }
}
