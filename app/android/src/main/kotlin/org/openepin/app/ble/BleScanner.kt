package org.openepin.app.ble

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.os.ParcelUuid
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import org.openepin.core.Protocol

/**
 * Scans for pins advertising the image service. A pin only advertises for a minute
 * after its button is pressed. Caller must hold the scan permission.
 */
@SuppressLint("MissingPermission")
fun BluetoothAdapter.scanForPins(): Flow<ScanResult> = callbackFlow {
    val scanner = bluetoothLeScanner
    if (scanner == null || !isEnabled) {
        close(IllegalStateException("Bluetooth is off"))
        return@callbackFlow
    }
    val callback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            trySend(result)
        }

        override fun onBatchScanResults(results: MutableList<ScanResult>) {
            results.forEach { trySend(it) }
        }

        override fun onScanFailed(errorCode: Int) {
            close(IllegalStateException("Scan failed ($errorCode)"))
        }
    }
    val filters = listOf(
        ScanFilter.Builder().setServiceUuid(ParcelUuid(Protocol.SERVICE)).build(),
    )
    val settings = ScanSettings.Builder()
        .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
        .build()
    scanner.startScan(filters, settings, callback)
    awaitClose { scanner.stopScan(callback) }
}
