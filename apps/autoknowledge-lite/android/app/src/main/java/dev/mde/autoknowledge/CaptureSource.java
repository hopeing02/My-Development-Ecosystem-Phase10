package dev.mde.autoknowledge;

enum CaptureSource {
    CHATGPT("chatgpt", "chatgpt_android", "ChatGPT", "ChatGPT 답변"),
    CODEX("codex", "codex_remote_android", "Codex", "Codex 답변"),
    GENERAL("general", "android_clipboard", "일반 문서", "클립보드 문서");

    final String sourceType;
    final String sourceApp;
    final String displayName;
    final String titlePrefix;

    CaptureSource(String sourceType, String sourceApp, String displayName, String titlePrefix) {
        this.sourceType = sourceType;
        this.sourceApp = sourceApp;
        this.displayName = displayName;
        this.titlePrefix = titlePrefix;
    }

    static CaptureSource fromStored(String value) {
        try {
            return valueOf(value);
        } catch (IllegalArgumentException | NullPointerException error) {
            return CHATGPT;
        }
    }
}
