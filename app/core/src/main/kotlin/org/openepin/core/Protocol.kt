package org.openepin.core

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.UUID
import java.util.zip.CRC32

/**
 * The Open E-Pin BLE protocol, version 1. Defined in docs/ble-protocol.md; keep in step
 * with firmware/src/proto.h.
 */
object Protocol {
    const val VERSION = 1

    val SERVICE: UUID = UUID.fromString("7a1e0001-3c4d-4b5e-9f60-0e9e0e9e0e9e")
    val INFO: UUID = UUID.fromString("7a1e0002-3c4d-4b5e-9f60-0e9e0e9e0e9e")
    val CONTROL: UUID = UUID.fromString("7a1e0003-3c4d-4b5e-9f60-0e9e0e9e0e9e")
    val DATA: UUID = UUID.fromString("7a1e0004-3c4d-4b5e-9f60-0e9e0e9e0e9e")
    val CCC_DESCRIPTOR: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    const val FORMAT_4BPP = 0x01

    const val OP_START = 0x01
    const val OP_STATUS = 0x02
    const val OP_COMMIT = 0x03
    const val OP_ABORT = 0x04
    const val OP_CLEAR = 0x05
    const val OP_SLEEP = 0x06
    const val OP_RESPONSE = 0x80

    const val EVT_PROGRESS = 0x90
    const val EVT_NAK = 0x91
    const val EVT_REFRESH_DONE = 0xA0

    const val DATA_HEADER = 4

    /** ATT write header (opcode + handle) taken out of the MTU. */
    const val ATT_HEADER = 3

    /** Most bytes the app may send beyond the last PROGRESS. */
    const val WINDOW_BYTES = 16 * 1024

    fun crc32(data: ByteArray): Long = CRC32().apply { update(data) }.value

    fun start(format: Int, length: Int, crc: Long, imageId: Int): ByteArray =
        le(14).put(OP_START.toByte()).put(format.toByte()).putInt(length)
            .putInt(crc.toInt()).putInt(imageId).array()

    fun status(): ByteArray = byteArrayOf(OP_STATUS.toByte())
    fun commit(): ByteArray = byteArrayOf(OP_COMMIT.toByte())
    fun abort(): ByteArray = byteArrayOf(OP_ABORT.toByte())
    fun clear(color: PanelColor): ByteArray = byteArrayOf(OP_CLEAR.toByte(), color.code.toByte())
    fun sleep(): ByteArray = byteArrayOf(OP_SLEEP.toByte())

    fun dataPacket(offset: Int, image: ByteArray, length: Int): ByteArray {
        val out = ByteArray(DATA_HEADER + length)
        ByteBuffer.wrap(out).order(ByteOrder.LITTLE_ENDIAN).putInt(offset)
        System.arraycopy(image, offset, out, DATA_HEADER, length)
        return out
    }

    fun parseEvent(bytes: ByteArray): PinEvent {
        require(bytes.isNotEmpty()) { "Empty notification" }
        val op = bytes[0].toInt() and 0xFF
        val buf = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        return when {
            op == EVT_PROGRESS && bytes.size >= 5 -> PinEvent.Progress(buf.getInt(1))
            op == EVT_NAK && bytes.size >= 5 -> PinEvent.Nak(buf.getInt(1))
            op == EVT_REFRESH_DONE && bytes.size >= 2 -> PinEvent.RefreshDone(Status.of(bytes[1]))
            op and OP_RESPONSE != 0 && op < EVT_PROGRESS && bytes.size >= 2 ->
                PinEvent.Response(op and 0x7F, Status.of(bytes[1]), bytes.copyOfRange(2, bytes.size))
            else -> PinEvent.Unknown(bytes)
        }
    }

    internal fun le(size: Int): ByteBuffer = ByteBuffer.allocate(size).order(ByteOrder.LITTLE_ENDIAN)
}

enum class Status(val code: Int) {
    OK(0),
    BAD_LENGTH(1),
    BAD_STATE(2),
    CRC_MISMATCH(3),
    BAD_FORMAT(4),
    BUSY(5),
    BAD_OFFSET(6),
    LOW_BATTERY(7),
    PANEL_ERROR(8),
    UNKNOWN_OPCODE(9),
    UNKNOWN(-1);

    companion object {
        fun of(b: Byte): Status = entries.firstOrNull { it.code == (b.toInt() and 0xFF) } ?: UNKNOWN
    }
}

enum class TransferState { IDLE, RECEIVING, READY, REFRESHING, UNKNOWN }

sealed class PinEvent {
    /** Answer to a request; [op] is the request opcode. */
    data class Response(val op: Int, val status: Status, val payload: ByteArray) : PinEvent() {
        val u32: Int get() = ByteBuffer.wrap(payload).order(ByteOrder.LITTLE_ENDIAN).getInt(0)
    }
    data class Progress(val offset: Int) : PinEvent()
    data class Nak(val expectedOffset: Int) : PinEvent()
    data class RefreshDone(val status: Status) : PinEvent()
    class Unknown(val raw: ByteArray) : PinEvent()
}

/** Contents of the Info characteristic. */
data class PinInfo(
    val protocolVersion: Int,
    val hardwareRevision: Int,
    val width: Int,
    val height: Int,
    val formats: Int,
    val state: TransferState,
    val batteryMillivolts: Int,
    val batteryPercent: Int,
    val charging: Boolean,
    val usbPower: Boolean,
    val firmwareVersion: String,
) {
    fun supports(format: Int): Boolean = formats and (1 shl (format - 1)) != 0

    companion object {
        fun parse(bytes: ByteArray): PinInfo {
            require(bytes.size >= 15) { "Info is ${bytes.size} bytes, expected 16" }
            val b = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
            fun u8(i: Int) = bytes[i].toInt() and 0xFF
            fun u16(i: Int) = b.getShort(i).toInt() and 0xFFFF
            return PinInfo(
                protocolVersion = u8(0),
                hardwareRevision = u8(1),
                width = u16(2),
                height = u16(4),
                formats = u8(6),
                state = TransferState.entries.getOrElse(u8(7)) { TransferState.UNKNOWN },
                batteryMillivolts = u16(8),
                batteryPercent = u8(10),
                charging = u8(11) and 1 != 0,
                usbPower = u8(11) and 2 != 0,
                firmwareVersion = "${u8(12)}.${u8(13)}.${u8(14)}",
            )
        }
    }
}

class PinException(val status: Status, message: String) : Exception("$message: $status")
