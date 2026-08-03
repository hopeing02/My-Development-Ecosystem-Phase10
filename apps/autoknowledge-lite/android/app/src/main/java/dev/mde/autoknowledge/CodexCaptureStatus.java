package dev.mde.autoknowledge;

import org.json.JSONObject;

final class CodexCaptureStatus {
    final String captureSessionId;
    final String state;
    final int messageCount;
    final int revision;
    final String documentId;
    final String viewerUrl;

    CodexCaptureStatus(
            String captureSessionId,
            String state,
            int messageCount,
            int revision,
            String documentId,
            String viewerUrl
    ) {
        this.captureSessionId = captureSessionId;
        this.state = state;
        this.messageCount = messageCount;
        this.revision = revision;
        this.documentId = documentId;
        this.viewerUrl = viewerUrl;
    }

    static CodexCaptureStatus fromJson(JSONObject value) {
        return new CodexCaptureStatus(
                value.optString("captureSessionId"),
                value.optString("state"),
                value.optInt("messageCount", value.optInt("totalMessages", 0)),
                value.isNull("revision") ? 0 : value.optInt("revision"),
                value.optString("documentId"),
                value.optString("viewerUrl")
        );
    }

    String label() {
        String revisionLabel = revision > 0 ? " · revision " + revision : "";
        return "상태: " + (state.isEmpty() ? "수집 중" : state)
                + " · 메시지 " + messageCount + "개" + revisionLabel;
    }
}
