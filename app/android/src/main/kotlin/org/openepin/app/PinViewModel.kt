package org.openepin.app

import android.annotation.SuppressLint
import android.app.Application
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.graphics.Bitmap
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.openepin.app.ble.PinConnection
import org.openepin.app.ble.scanForPins
import org.openepin.app.image.BitmapPipeline
import org.openepin.app.image.CropState
import org.openepin.core.ImageProcessor
import org.openepin.core.PanelColor
import org.openepin.core.PinException
import org.openepin.core.PinInfo
import org.openepin.core.ProcessOptions
import org.openepin.core.Protocol
import org.openepin.core.Status
import org.openepin.core.Uploader
import java.io.IOException
import kotlin.random.Random

data class FoundPin(val device: BluetoothDevice, val name: String, val rssi: Int) {
    val address: String get() = device.address
}

enum class Link { DISCONNECTED, CONNECTING, CONNECTED }

sealed class UploadUi {
    data object Idle : UploadUi()
    data class Sending(val fraction: Float) : UploadUi()
    data object Refreshing : UploadUi()
    data object Done : UploadUi()
    data class Failed(val message: String, val canResume: Boolean) : UploadUi()
}

data class UiState(
    val scanning: Boolean = false,
    val found: List<FoundPin> = emptyList(),
    val link: Link = Link.DISCONNECTED,
    val pinName: String? = null,
    val info: PinInfo? = null,
    val source: Bitmap? = null,
    val crop: CropState = CropState(),
    val options: ProcessOptions = ProcessOptions(),
    val preview: Bitmap? = null,
    val processing: Boolean = false,
    val upload: UploadUi = UploadUi.Idle,
    val error: String? = null,
)

/**
 * App state: scanning, the connection, the picked image and its processed version, and
 * the upload. Permissions are checked by MainActivity before any Bluetooth call.
 */
@SuppressLint("MissingPermission")
class PinViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private val adapter = app.getSystemService(BluetoothManager::class.java)?.adapter

    private var scanJob: Job? = null
    private var processJob: Job? = null
    private var uploadJob: Job? = null
    private var connection: PinConnection? = null
    private var lastDevice: BluetoothDevice? = null

    /** Packed frame for the current preview, and its id (kept for resume). */
    private var packed: ByteArray? = null
    private var imageId: Int = 0

    // ---- scanning and connection -------------------------------------------------

    fun startScan() {
        val a = adapter ?: return fail("This phone has no Bluetooth")
        scanJob?.cancel()
        _state.update { it.copy(scanning = true, found = emptyList(), error = null) }
        scanJob = viewModelScope.launch {
            try {
                withTimeoutOrNull(30_000) {
                    a.scanForPins().collect { r ->
                        val pin = FoundPin(r.device, r.scanRecord?.deviceName ?: r.device.name ?: "Open E-Pin", r.rssi)
                        _state.update { s ->
                            s.copy(found = (s.found.filterNot { it.address == pin.address } + pin).sortedByDescending { it.rssi })
                        }
                    }
                }
            } catch (e: IllegalStateException) {
                fail(e.message ?: "Scan failed")
            } finally {
                _state.update { it.copy(scanning = false) }
            }
        }
    }

    fun stopScan() {
        scanJob?.cancel()
    }

    fun connect(pin: FoundPin) = connect(pin.device, pin.name)

    private fun connect(device: BluetoothDevice, name: String?) {
        stopScan()
        lastDevice = device
        _state.update { it.copy(link = Link.CONNECTING, pinName = name, error = null) }
        viewModelScope.launch {
            try {
                val c = PinConnection.connect(getApplication(), device)
                connection = c
                _state.update { it.copy(link = Link.CONNECTED, info = c.readInfo()) }
                watch(c)
            } catch (e: Exception) {
                _state.update { it.copy(link = Link.DISCONNECTED) }
                fail("Could not connect: ${e.message}. Press the pin's button and try again.")
            }
        }
    }

    private fun watch(c: PinConnection) = viewModelScope.launch {
        c.connected.collect { up ->
            if (!up && connection === c) {
                connection = null
                c.close()
                _state.update { it.copy(link = Link.DISCONNECTED) }
            }
        }
    }

    fun disconnect() {
        uploadJob?.cancel()
        connection?.close()
        connection = null
        _state.update { it.copy(link = Link.DISCONNECTED, info = null) }
    }

    fun refreshInfo() = viewModelScope.launch {
        val c = connection ?: return@launch
        runCatching { c.readInfo() }.onSuccess { info -> _state.update { it.copy(info = info) } }
    }

    // ---- image ----------------------------------------------------------------------

    fun pickImage(uri: Uri) = viewModelScope.launch {
        try {
            val bmp = withContext(Dispatchers.IO) { BitmapPipeline.decode(getApplication(), uri) }
            _state.update { it.copy(source = bmp, crop = CropState(), upload = UploadUi.Idle) }
            reprocess(immediate = true)
        } catch (e: Exception) {
            fail("Could not open that image: ${e.message}")
        }
    }

    fun setCrop(crop: CropState) {
        _state.update { it.copy(crop = crop) }
        reprocess()
    }

    fun setOptions(options: ProcessOptions) {
        _state.update { it.copy(options = options) }
        reprocess(immediate = true)
    }

    /** Crop, scale, dither and pack in the background; restarts when the input changes. */
    private fun reprocess(immediate: Boolean = false) {
        val s = _state.value
        val src = s.source ?: return
        processJob?.cancel()
        processJob = viewModelScope.launch {
            if (!immediate) delay(250) // wait for the gesture to settle
            _state.update { it.copy(processing = true) }
            val (preview, frame) = withContext(Dispatchers.Default) {
                val square = BitmapPipeline.renderCrop(src, s.crop)
                val img = ImageProcessor.process(BitmapPipeline.pixels(square), s.options)
                BitmapPipeline.preview(img) to img.pack()
            }
            packed = frame
            imageId = Random.nextInt()
            _state.update { it.copy(preview = preview, processing = false, upload = UploadUi.Idle) }
        }
    }

    // ---- upload -----------------------------------------------------------------------

    /** Sends the current image. After a dropped link, call again to resume. */
    fun upload() {
        val frame = packed ?: return
        val id = imageId
        uploadJob?.cancel()
        uploadJob = viewModelScope.launch {
            _state.update { it.copy(upload = UploadUi.Sending(0f), error = null) }
            try {
                val c = connection ?: reconnect()
                Uploader(c).upload(frame, id) { p ->
                    _state.update {
                        it.copy(
                            upload = if (p.acknowledged >= p.total) UploadUi.Refreshing
                            else UploadUi.Sending(p.fraction),
                        )
                    }
                }
                _state.update { it.copy(upload = UploadUi.Done) }
                refreshInfo()
            } catch (e: PinException) {
                val msg = when (e.status) {
                    Status.LOW_BATTERY -> "The pin's battery is too low to refresh. Charge it and retry."
                    Status.BUSY -> "The pin is still drawing. Retry in a moment."
                    else -> e.message ?: "Upload failed"
                }
                _state.update { it.copy(upload = UploadUi.Failed(msg, canResume = e.status != Status.CRC_MISMATCH)) }
            } catch (e: TimeoutCancellationException) {
                _state.update { it.copy(upload = UploadUi.Failed("The pin stopped answering.", canResume = true)) }
            } catch (e: IOException) {
                _state.update {
                    it.copy(upload = UploadUi.Failed("Connection lost. Press the pin's button, then Retry to resume.", canResume = true))
                }
            }
        }
    }

    private suspend fun reconnect(): PinConnection {
        val d = lastDevice ?: throw IOException("No pin selected")
        _state.update { it.copy(link = Link.CONNECTING) }
        val c = PinConnection.connect(getApplication(), d)
        connection = c
        _state.update { it.copy(link = Link.CONNECTED) }
        watch(c)
        return c
    }

    fun clearPanel(color: PanelColor = PanelColor.WHITE) = sendSimple(Protocol.clear(color))

    fun sleepPin() = sendSimple(Protocol.sleep())

    private fun sendSimple(cmd: ByteArray) = viewModelScope.launch {
        val c = connection ?: return@launch
        try {
            c.writeControl(cmd)
        } catch (e: IOException) {
            fail(e.message ?: "Write failed")
        }
    }

    fun dismissError() = _state.update { it.copy(error = null) }

    private fun fail(msg: String) = _state.update { it.copy(error = msg) }

    override fun onCleared() {
        connection?.close()
    }
}
