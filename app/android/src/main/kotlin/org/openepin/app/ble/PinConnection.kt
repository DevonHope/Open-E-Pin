package org.openepin.app.ble

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.content.Context
import android.os.Build
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeout
import org.openepin.core.PinInfo
import org.openepin.core.PinLink
import org.openepin.core.Protocol
import java.io.IOException

/**
 * One GATT connection to a pin, with coroutine wrappers. Android allows one GATT
 * operation at a time, so every operation goes through [op], which waits for its callback.
 * Caller must hold BLUETOOTH_CONNECT (Android 12+).
 */
@SuppressLint("MissingPermission")
class PinConnection private constructor(
    private val context: Context,
    val device: BluetoothDevice,
) : PinLink {

    private var gatt: BluetoothGatt? = null
    private val opLock = Mutex()
    @Volatile private var pending: CompletableDeferred<Any?>? = null
    @Volatile private var connectWait: CompletableDeferred<Unit>? = null

    private lateinit var info: BluetoothGattCharacteristic
    private lateinit var control: BluetoothGattCharacteristic
    private lateinit var data: BluetoothGattCharacteristic

    private val _notifications = MutableSharedFlow<ByteArray>(extraBufferCapacity = 256)
    override val notifications: SharedFlow<ByteArray> = _notifications.asSharedFlow()

    private val _connected = MutableStateFlow(false)
    val connected: StateFlow<Boolean> = _connected.asStateFlow()

    @Volatile override var mtu: Int = 23
        private set

    private class Refused : IOException("GATT operation refused (busy)")

    private val callback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) {
                _connected.value = true
                connectWait?.complete(Unit)
            } else {
                _connected.value = false
                val e = IOException("Disconnected (status $status)")
                connectWait?.completeExceptionally(e)
                pending?.completeExceptionally(e)
            }
        }

        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) = complete(status, Unit)

        override fun onMtuChanged(g: BluetoothGatt, mtu: Int, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) this@PinConnection.mtu = mtu
            // A refused MTU is not fatal: keep the default.
            complete(BluetoothGatt.GATT_SUCCESS, mtu)
        }

        override fun onCharacteristicWrite(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) =
            complete(status, Unit)

        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) =
            complete(status, Unit)

        // Android 13+
        override fun onCharacteristicRead(
            g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray, status: Int,
        ) = complete(status, value)

        @Deprecated("Android 12 and older")
        override fun onCharacteristicRead(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) {
            @Suppress("DEPRECATION")
            complete(status, c.value)
        }

        // Android 13+
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) {
            if (c.uuid == Protocol.CONTROL) _notifications.tryEmit(value)
        }

        @Deprecated("Android 12 and older")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            @Suppress("DEPRECATION")
            if (c.uuid == Protocol.CONTROL) _notifications.tryEmit(c.value.copyOf())
        }
    }

    private fun complete(status: Int, value: Any?) {
        val d = pending ?: return
        if (status == BluetoothGatt.GATT_SUCCESS) d.complete(value)
        else d.completeExceptionally(IOException("GATT error $status"))
    }

    @Suppress("UNCHECKED_CAST")
    private suspend fun <T> op(timeoutMs: Long = 10_000, start: (BluetoothGatt) -> Boolean): T =
        opLock.withLock {
            val g = gatt ?: throw IOException("Not connected")
            val d = CompletableDeferred<Any?>()
            pending = d
            try {
                if (!start(g)) throw Refused()
                withTimeout(timeoutMs) { d.await() } as T
            } finally {
                pending = null
            }
        }

    private suspend fun open() {
        val wait = CompletableDeferred<Unit>()
        connectWait = wait
        gatt = device.connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE)
        try {
            withTimeout(15_000) { wait.await() }

            op<Int> { it.requestMtu(247) }
            gatt?.setPreferredPhy(
                BluetoothDevice.PHY_LE_2M_MASK, BluetoothDevice.PHY_LE_2M_MASK, BluetoothDevice.PHY_OPTION_NO_PREFERRED,
            )
            gatt?.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH)
            op<Unit>(timeoutMs = 15_000) { it.discoverServices() }

            val svc = gatt?.getService(Protocol.SERVICE) ?: throw IOException("Not an Open E-Pin (service missing)")
            info = svc.getCharacteristic(Protocol.INFO) ?: throw IOException("Info characteristic missing")
            control = svc.getCharacteristic(Protocol.CONTROL) ?: throw IOException("Control characteristic missing")
            data = svc.getCharacteristic(Protocol.DATA) ?: throw IOException("Data characteristic missing")

            enableNotifications(control)
        } catch (e: Throwable) {
            close()
            throw e
        }
    }

    private suspend fun enableNotifications(c: BluetoothGattCharacteristic) {
        val g = gatt ?: throw IOException("Not connected")
        g.setCharacteristicNotification(c, true)
        val ccc = c.getDescriptor(Protocol.CCC_DESCRIPTOR) ?: throw IOException("CCC descriptor missing")
        val enable = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        op<Unit> {
            if (Build.VERSION.SDK_INT >= 33) {
                it.writeDescriptor(ccc, enable) == BluetoothStatusCodes.SUCCESS
            } else {
                @Suppress("DEPRECATION")
                ccc.value = enable
                @Suppress("DEPRECATION")
                it.writeDescriptor(ccc)
            }
        }
    }

    private suspend fun write(c: BluetoothGattCharacteristic, value: ByteArray, type: Int) {
        repeat(100) {
            try {
                op<Unit> {
                    if (Build.VERSION.SDK_INT >= 33) {
                        it.writeCharacteristic(c, value, type) == BluetoothStatusCodes.SUCCESS
                    } else {
                        c.writeType = type
                        @Suppress("DEPRECATION")
                        c.value = value
                        @Suppress("DEPRECATION")
                        it.writeCharacteristic(c)
                    }
                }
                return
            } catch (e: Refused) {
                if (!_connected.value) throw IOException("Disconnected")
                delay(5) // stack queue full; try again shortly
            }
        }
        throw IOException("Write kept being refused")
    }

    override suspend fun writeControl(value: ByteArray) =
        write(control, value, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT)

    override suspend fun writeData(value: ByteArray) =
        write(data, value, BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE)

    suspend fun readInfo(): PinInfo = PinInfo.parse(op<ByteArray> { it.readCharacteristic(info) })

    fun close() {
        gatt?.let {
            it.disconnect()
            it.close()
        }
        gatt = null
        _connected.value = false
        pending?.completeExceptionally(IOException("Closed"))
    }

    companion object {
        /** Connects, negotiates MTU/PHY, discovers the service and enables notifications. */
        suspend fun connect(context: Context, device: BluetoothDevice): PinConnection =
            PinConnection(context.applicationContext, device).also { it.open() }
    }
}
