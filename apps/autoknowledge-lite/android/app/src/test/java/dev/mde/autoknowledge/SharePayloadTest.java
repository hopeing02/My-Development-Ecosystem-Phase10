package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class SharePayloadTest {
    @Test
    public void extractsTitleContentAndUrl() {
        SharePayload payload = SharePayload.from(
                "Article title", "Read this https://example.com/page."
        );

        assertEquals("Article title", payload.title);
        assertEquals("Read this https://example.com/page.", payload.content);
        assertEquals("https://example.com/page", payload.sourceUrl);
        assertTrue(payload.isValid());
    }

    @Test
    public void rejectsMissingSharedText() {
        SharePayload payload = SharePayload.from("Title", null);

        assertFalse(payload.isValid());
    }
}
