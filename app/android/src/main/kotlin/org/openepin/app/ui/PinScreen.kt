package org.openepin.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import org.openepin.app.FoundPin
import org.openepin.app.Link
import org.openepin.app.UiState
import org.openepin.app.UploadUi
import org.openepin.core.DitherMethod
import org.openepin.core.PinInfo
import org.openepin.core.ProcessOptions

class PinActions(
    val scan: () -> Unit,
    val connect: (FoundPin) -> Unit,
    val disconnect: () -> Unit,
    val pickImage: () -> Unit,
    val setCrop: (org.openepin.app.image.CropState) -> Unit,
    val setOptions: (ProcessOptions) -> Unit,
    val upload: () -> Unit,
    val clear: () -> Unit,
    val sleep: () -> Unit,
    val dismissError: () -> Unit,
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PinScreen(state: UiState, actions: PinActions) {
    Scaffold(topBar = { TopAppBar(title = { Text("Open E-Pin") }) }) { pad ->
        Column(
            Modifier
                .padding(pad)
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            state.error?.let { ErrorCard(it, actions.dismissError) }

            when (state.link) {
                Link.CONNECTED -> PinCard(state.pinName, state.info, actions)
                Link.CONNECTING -> Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(20.dp))
                    Spacer(Modifier.width(12.dp))
                    Text("Connecting…")
                }
                Link.DISCONNECTED -> ScanSection(state, actions)
            }

            ImageSection(state, actions)
        }
    }
}

@Composable
private fun ErrorCard(message: String, onDismiss: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(message, Modifier.weight(1f), color = MaterialTheme.colorScheme.error)
            TextButton(onClick = onDismiss) { Text("OK") }
        }
    }
}

@Composable
private fun ScanSection(state: UiState, actions: PinActions) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Press the button on the pin, then search.", style = MaterialTheme.typography.bodyMedium)
        Button(onClick = actions.scan, enabled = !state.scanning) {
            Text(if (state.scanning) "Searching…" else "Find pins")
        }
        state.found.forEach { pin ->
            Card(
                Modifier
                    .fillMaxWidth()
                    .clickable { actions.connect(pin) },
            ) {
                Row(Modifier.padding(12.dp)) {
                    Text(pin.name, Modifier.weight(1f))
                    Text("${pin.rssi} dBm", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun PinCard(name: String?, info: PinInfo?, actions: PinActions) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(name ?: "Open E-Pin", style = MaterialTheme.typography.titleMedium)
            if (info != null) {
                val charge = if (info.charging) ", charging" else ""
                Text("Battery ${info.batteryPercent}% (${info.batteryMillivolts} mV)$charge")
                Text("Firmware ${info.firmwareVersion}, protocol ${info.protocolVersion}", style = MaterialTheme.typography.bodySmall)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = actions.clear) { Text("Clear") }
                OutlinedButton(onClick = actions.sleep) { Text("Sleep") }
                OutlinedButton(onClick = actions.disconnect) { Text("Disconnect") }
            }
        }
    }
}

@Composable
private fun ImageSection(state: UiState, actions: PinActions) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Button(onClick = actions.pickImage) { Text(if (state.source == null) "Pick an image" else "Pick another image") }

        val src = state.source
        if (src != null) {
            val srcImage = remember(src) { src.asImageBitmap() }

            Text("Drag and pinch to place the image in the circle.", style = MaterialTheme.typography.bodySmall)
            CircleCropper(srcImage, state.crop, actions.setCrop, Modifier.fillMaxWidth())

            OptionsRow(state.options, actions.setOptions)

            Text("On the pin", style = MaterialTheme.typography.titleSmall)
            Row(verticalAlignment = Alignment.CenterVertically) {
                state.preview?.let { p ->
                    val img = remember(p) { p.asImageBitmap() }
                    Image(img, "Preview of the dithered image", Modifier.size(200.dp).clip(CircleShape))
                }
                if (state.processing) {
                    Spacer(Modifier.width(12.dp))
                    CircularProgressIndicator(Modifier.size(20.dp))
                }
            }

            UploadControls(state, actions)
        }
    }
}

@Composable
private fun OptionsRow(options: ProcessOptions, onChange: (ProcessOptions) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            DitherMethod.entries.forEach { m ->
                FilterChip(
                    selected = options.dither == m,
                    onClick = { onChange(options.copy(dither = m)) },
                    label = {
                        Text(
                            when (m) {
                                DitherMethod.NONE -> "Flat"
                                DitherMethod.FLOYD_STEINBERG -> "Photo"
                                DitherMethod.ATKINSON -> "Crisp"
                            },
                        )
                    },
                )
            }
        }
        Text("Saturation ${"%.1f".format(options.saturation)}", style = MaterialTheme.typography.bodySmall)
        Slider(
            value = options.saturation,
            onValueChange = { onChange(options.copy(saturation = it)) },
            valueRange = 0.5f..2.5f,
        )
        Text("Contrast ${"%.1f".format(options.contrast)}", style = MaterialTheme.typography.bodySmall)
        Slider(
            value = options.contrast,
            onValueChange = { onChange(options.copy(contrast = it)) },
            valueRange = 0.5f..2f,
        )
        OutlinedButton(onClick = { onChange(options.copy(rotation = (options.rotation + 90) % 360)) }) {
            Text("Rotate (${options.rotation}°)")
        }
    }
}

@Composable
private fun UploadControls(state: UiState, actions: PinActions) {
    val ready = state.preview != null && !state.processing
    when (val u = state.upload) {
        is UploadUi.Sending -> {
            Text("Sending… ${(u.fraction * 100).toInt()}%")
            LinearProgressIndicator(progress = { u.fraction }, modifier = Modifier.fillMaxWidth())
        }
        UploadUi.Refreshing -> {
            Text("Drawing on the pin (about 20 s)…")
            LinearProgressIndicator(Modifier.fillMaxWidth())
        }
        UploadUi.Done -> {
            Text("Done.")
            Button(onClick = actions.upload, enabled = ready && state.link == Link.CONNECTED) { Text("Send again") }
        }
        is UploadUi.Failed -> {
            Text(u.message, color = MaterialTheme.colorScheme.error)
            Button(onClick = actions.upload, enabled = ready) { Text(if (u.canResume) "Retry" else "Send again") }
        }
        UploadUi.Idle -> {
            Button(onClick = actions.upload, enabled = ready && state.link == Link.CONNECTED) { Text("Send to pin") }
        }
    }
}
