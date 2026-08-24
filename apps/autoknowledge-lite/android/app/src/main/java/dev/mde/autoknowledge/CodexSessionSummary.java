package dev.mde.autoknowledge;

import org.json.JSONObject;

final class CodexSessionSummary {
    final String sourceSessionId;
    final String title;
    final String updatedAt;
    final String clientType;
    final int messageCount;

    CodexSessionSummary(
            String sourceSessionId,
            String title,
            String updatedAt,
            String clientType,
            int messageCount
    ) {
        this.sourceSessionId = sourceSessionId;
        this.title = title;
        this.updatedAt = updatedAt;
        this.clientType = clientType;
        this.messageCount = messageCount;
    }

    static CodexSessionSummary fromJson(JSONObject value) {
        return new CodexSessionSummary(
                value.optString("sourceSessionId"),
                value.optString("title", "제목 없는 Codex 세션"),
                value.optString("updatedAt"),
                value.optString("clientType", "codex"),
                value.optInt("messageCount", -1)
        );
    }

    String label() {
        String count = messageCount < 0 ? "메시지 수 확인 전" : messageCount + "개 메시지";
        return title + "\n" + updatedAt + " · " + count + " · " + clientType;
    }
}
