package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class SharePayloadTest {
    @Test
    public void extractsTitleContentUrlAndDefaultFolder() {
        SharePayload payload = SharePayload.from(
                "Article title", "Read this https://example.com/page."
        );

        assertEquals("Article title", payload.title);
        assertEquals("Read this https://example.com/page.", payload.content);
        assertEquals("https://example.com/page", payload.sourceUrl);
        assertEquals("00_Inbox", payload.targetFolder);
        assertTrue(payload.isValid());
    }

    @Test
    public void rejectsMissingSharedText() {
        SharePayload payload = SharePayload.from("Title", null);

        assertFalse(payload.isValid());
    }

    @Test
    public void createsClipboardPayloadWithSelectedFolder() {
        SharePayload payload = SharePayload.fromClipboard(
                "전체 채팅 제목\n첫 번째 메시지\n두 번째 메시지 https://example.com/chat",
                "20_Learning"
        );

        assertEquals("전체 채팅 제목", payload.title);
        assertEquals(
                "전체 채팅 제목\n첫 번째 메시지\n두 번째 메시지 https://example.com/chat",
                payload.content
        );
        assertEquals("https://example.com/chat", payload.sourceUrl);
        assertEquals("20_Learning", payload.targetFolder);
    }

    @Test
    public void fallsBackToInboxForUnapprovedFolder() {
        SharePayload payload = SharePayload.from("Title", "Content", "../outside");

        assertEquals("00_Inbox", payload.targetFolder);
        assertEquals(0, SharePayload.folderIndex("../outside"));
    }

    @Test
    public void exposesSixApprovedFolders() {
        assertEquals(6, SharePayload.VAULT_FOLDERS.length);
        assertEquals("90_Archive", SharePayload.VAULT_FOLDERS[5]);
    }
}
