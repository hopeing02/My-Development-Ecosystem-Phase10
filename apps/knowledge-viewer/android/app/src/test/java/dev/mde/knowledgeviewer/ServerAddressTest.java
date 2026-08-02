package dev.mde.knowledgeviewer;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class ServerAddressTest {
    @Test
    public void normalizesServerAddress() {
        assertEquals("http://192.168.0.10:8765", ServerAddress.normalize(" http://192.168.0.10:8765/ "));
    }

    @Test
    public void rejectsPathAndCredentials() {
        assertThrows(IllegalArgumentException.class, () -> ServerAddress.normalize("http://pc:8765/private"));
        assertThrows(IllegalArgumentException.class, () -> ServerAddress.normalize("http://user@pc:8765"));
    }

    @Test
    public void comparesOriginsWithDefaultPorts() {
        assertTrue(ServerAddress.sameOrigin("https://viewer.local", "https://viewer.local/docs"));
        assertFalse(ServerAddress.sameOrigin("https://viewer.local", "https://other.local/"));
        assertFalse(ServerAddress.sameOrigin("http://viewer.local", "https://viewer.local/"));
    }
}
