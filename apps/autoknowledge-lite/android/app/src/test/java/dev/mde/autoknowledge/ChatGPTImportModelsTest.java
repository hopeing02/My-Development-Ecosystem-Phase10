package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;
import static org.junit.Assert.assertTrue;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Test;

public final class ChatGPTImportModelsTest {
    @Test
    public void resultShowsProjectionAndWarningCountsWithoutImportId() throws Exception {
        ChatGPTImportResult result = ChatGPTImportResult.fromJson(new JSONObject()
                .put("status", "partial")
                .put("importId", "private-import-id")
                .put("discoveredSessions", 3)
                .put("projectedSessions", 2)
                .put("duplicateSessions", 0)
                .put("failedSessions", 1)
                .put("warnings", new JSONArray().put(new JSONObject().put("code", "DAMAGED"))));

        assertTrue(result.label().contains("일부 세션 가져오기 완료"));
        assertTrue(result.label().contains("신규 2"));
        assertTrue(result.label().contains("경고 1"));
        assertTrue(!result.label().contains("private-import-id"));
    }

    @Test
    public void validatorCanonicalizesSafeMobileCopyVariants() {
        String valid = "https://chatgpt.com/share/12345678-abcd-4321-abcd-1234567890ab";

        assertEquals(valid, ChatGPTSharedLinkValidator.validate(" " + valid + " "));
        assertEquals(valid, ChatGPTSharedLinkValidator.validate(valid + "?tracking=true#copy"));
        assertEquals(valid, ChatGPTSharedLinkValidator.validate("\u200B" + valid + "\uFEFF"));
        assertThrows(IllegalArgumentException.class, () ->
                ChatGPTSharedLinkValidator.validate(
                        "https://chatgpt.com.evil.test/share/12345678"
                ));
        assertThrows(IllegalArgumentException.class, () ->
                ChatGPTSharedLinkValidator.validate("http://chatgpt.com/share/12345678"));
    }
}
