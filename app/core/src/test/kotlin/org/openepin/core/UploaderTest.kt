package org.openepin.core

import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.IOException
import kotlin.random.Random

class UploaderTest {
    private val image = Random(42).nextBytes(Panel.FRAME_BYTES)

    @Test
    fun uploadsWholeImage() = runTest {
        val pin = FakePin()
        var last: UploadProgress? = null
        Uploader(pin.link()).upload(image, imageId = 1) { last = it }
        assertArrayEquals(image, pin.refreshed)
        assertEquals(Panel.FRAME_BYTES, last!!.acknowledged)
    }

    @Test
    fun smallMtuStillWorks() = runTest {
        val pin = FakePin()
        Uploader(pin.link(mtu = 23)).upload(image, imageId = 2)
        assertArrayEquals(image, pin.refreshed)
    }

    @Test
    fun rewindsAfterNak() = runTest {
        val pin = FakePin().apply { dropOnceAtOffset = 240 * 10 }
        Uploader(pin.link()).upload(image, imageId = 3)
        assertArrayEquals(image, pin.refreshed)
    }

    @Test
    fun resumesAfterDisconnect() = runTest {
        val pin = FakePin().apply { disconnectAfterPackets = 150 }
        try {
            Uploader(pin.link()).upload(image, imageId = 4)
            fail("expected the link to drop")
        } catch (e: IOException) {
            // expected
        }
        val partial = pin.offset
        assertTrue("pin kept partial data", partial > 0)

        pin.disconnectAfterPackets = null
        var firstReported = -1
        Uploader(pin.link()).upload(image, imageId = 4) { if (firstReported < 0) firstReported = it.acknowledged }
        assertEquals("resumed where the pin stopped", partial, firstReported)
        assertArrayEquals(image, pin.refreshed)
    }

    @Test
    fun crcMismatchIsReported() = runTest {
        val pin = FakePin().apply { corrupt = true }
        try {
            Uploader(pin.link()).upload(image, imageId = 5)
            fail("expected CRC mismatch")
        } catch (e: PinException) {
            assertEquals(Status.CRC_MISMATCH, e.status)
        }
    }
}
