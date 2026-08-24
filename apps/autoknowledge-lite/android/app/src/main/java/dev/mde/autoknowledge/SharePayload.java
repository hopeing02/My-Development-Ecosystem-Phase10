package dev.mde.autoknowledge;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class SharePayload {
    static final String DEFAULT_VAULT_FOLDER = "00_Inbox";
    static final String[] VAULT_FOLDERS = {
            "00_Inbox",
            "10_Life",
            "20_Learning",
            "30_Interests",
            "40_Reference",
            "90_Archive"
    };
    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");

    final String title;
    final String content;
    final String sourceUrl;
    final String targetFolder;
    final String captureOrigin;
    final String parentDocumentId;
    final String sourceType;
    final String sourceApp;
    final String contentHash;
    final String capturedAt;
    final String deviceId;

    private SharePayload(
            String title,
            String content,
            String sourceUrl,
            String targetFolder,
            String captureOrigin,
            String parentDocumentId,
            String sourceType,
            String sourceApp,
            String contentHash,
            String capturedAt,
            String deviceId
    ) {
        this.title = title;
        this.content = content;
        this.sourceUrl = sourceUrl;
        this.targetFolder = normalizeTargetFolder(targetFolder);
        this.captureOrigin = captureOrigin;
        this.parentDocumentId = parentDocumentId == null ? "" : parentDocumentId.trim();
        this.sourceType = sourceType;
        this.sourceApp = sourceApp;
        this.contentHash = contentHash;
        this.capturedAt = capturedAt;
        this.deviceId = deviceId;
    }

    static SharePayload from(CharSequence subject, CharSequence sharedText) {
        return from(subject, sharedText, DEFAULT_VAULT_FOLDER);
    }

    static SharePayload from(
            CharSequence subject,
            CharSequence sharedText,
            String targetFolder
    ) {
        String content = sharedText == null ? "" : sharedText.toString().trim();
        String title = subject == null ? "" : subject.toString().trim();
        Matcher matcher = URL_PATTERN.matcher(content);
        String sourceUrl = matcher.find() ? trimTrailingPunctuation(matcher.group()) : "";
        return new SharePayload(
                title,
                content,
                sourceUrl,
                targetFolder,
                "api",
                "",
                "general",
                "android_share",
                "",
                "",
                ""
        );
    }

    static SharePayload fromClipboard(CharSequence clipboardText) {
        return fromClipboard(clipboardText, DEFAULT_VAULT_FOLDER);
    }

    static SharePayload fromClipboard(CharSequence clipboardText, String targetFolder) {
        return fromClipboard(clipboardText, targetFolder, "");
    }

    static SharePayload fromClipboard(
            CharSequence clipboardText,
            String targetFolder,
            String parentDocumentId
    ) {
        String content = clipboardText == null ? "" : clipboardText.toString().trim();
        int lineBreak = content.indexOf('\n');
        String firstLine = (lineBreak >= 0 ? content.substring(0, lineBreak) : content).trim();
        String title = firstLine.startsWith("http://") || firstLine.startsWith("https://")
                ? "클립보드 메모"
                : firstLine;
        if (title.length() > 80) {
            title = title.substring(0, 80);
        }
        SharePayload base = from(title, content, targetFolder);
        return new SharePayload(
                base.title,
                base.content,
                base.sourceUrl,
                base.targetFolder,
                "android_clipboard",
                parentDocumentId,
                "general",
                "android_clipboard",
                "",
                "",
                ""
        );
    }

    static SharePayload fromCapture(CaptureRequest request) {
        return new SharePayload(
                request.source.titlePrefix,
                request.content,
                "",
                request.targetFolder,
                "android_clipboard",
                request.parentDocumentId,
                request.source.sourceType,
                request.source.sourceApp,
                request.contentHash,
                request.capturedAt,
                request.deviceId
        );
    }

    static int folderIndex(String value) {
        String normalized = normalizeTargetFolder(value);
        for (int index = 0; index < VAULT_FOLDERS.length; index++) {
            if (VAULT_FOLDERS[index].equals(normalized)) {
                return index;
            }
        }
        return 0;
    }

    boolean isValid() {
        return !content.trim().isEmpty();
    }

    private static String normalizeTargetFolder(String value) {
        if (value != null) {
            for (String folder : VAULT_FOLDERS) {
                if (folder.equals(value)) {
                    return folder;
                }
            }
        }
        return DEFAULT_VAULT_FOLDER;
    }

    private static String trimTrailingPunctuation(String value) {
        return value.replaceFirst("[),.;!?]+$", "");
    }
}
