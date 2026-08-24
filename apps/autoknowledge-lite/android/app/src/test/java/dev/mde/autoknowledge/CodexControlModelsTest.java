package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.json.JSONObject;
import org.junit.Test;

public final class CodexControlModelsTest {
    @Test
    public void sessionSummaryShowsTitleTimeCountAndClientWithoutSourceId() throws Exception {
        CodexSessionSummary summary = CodexSessionSummary.fromJson(new JSONObject()
                .put("sourceSessionId", "019-private-id")
                .put("title", "Capture relations")
                .put("updatedAt", "2026-08-03T12:00:00+09:00")
                .put("clientType", "codex_app_server")
                .put("messageCount", 76));

        assertTrue(summary.label().contains("Capture relations"));
        assertTrue(summary.label().contains("76개 메시지"));
        assertTrue(summary.label().contains("codex_app_server"));
        assertFalse(summary.label().contains("019-private-id"));
    }

    @Test
    public void captureStatusShowsSavedRevision() throws Exception {
        CodexCaptureStatus status = CodexCaptureStatus.fromJson(new JSONObject()
                .put("captureSessionId", "cap-1")
                .put("state", "SAVED")
                .put("messageCount", 76)
                .put("revision", 2)
                .put("documentId", "doc-1")
                .put("viewerUrl", "http://100.75.235.67:8765"));

        assertEquals("cap-1", status.captureSessionId);
        assertTrue(status.label().contains("SAVED"));
        assertTrue(status.label().contains("revision 2"));
        assertEquals("http://100.75.235.67:8765", status.viewerUrl);
    }

    @Test
    public void projectUsesDisplayNameButPreservesProjectId() throws Exception {
        CodexProject project = CodexProject.fromJson(new JSONObject()
                .put("projectId", "autoknowledge-lite")
                .put("displayName", "AutoKnowledge Lite"));

        assertEquals("autoknowledge-lite", project.projectId);
        assertEquals("AutoKnowledge Lite", project.toString());
    }
}
