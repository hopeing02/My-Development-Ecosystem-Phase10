package dev.mde.autoknowledge;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class SharePayload {
    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");

    final String title;
    final String content;
    final String sourceUrl;

    private SharePayload(String title, String content, String sourceUrl) {
        this.title = title;
        this.content = content;
        this.sourceUrl = sourceUrl;
    }

    static SharePayload from(CharSequence subject, CharSequence sharedText) {
        String content = sharedText == null ? "" : sharedText.toString().trim();
        String title = subject == null ? "" : subject.toString().trim();
        Matcher matcher = URL_PATTERN.matcher(content);
        String sourceUrl = matcher.find() ? trimTrailingPunctuation(matcher.group()) : "";
        return new SharePayload(title, content, sourceUrl);
    }

    static SharePayload fromClipboard(CharSequence clipboardText) {
        String content = clipboardText == null ? "" : clipboardText.toString().trim();
        int lineBreak = content.indexOf('\n');
        String firstLine = (lineBreak >= 0 ? content.substring(0, lineBreak) : content).trim();
        String title = firstLine.startsWith("http://") || firstLine.startsWith("https://")
                ? "클립보드 메모"
                : firstLine;
        if (title.length() > 80) {
            title = title.substring(0, 80);
        }
        return from(title, content);
    }

    boolean isValid() {
        return !content.trim().isEmpty();
    }

    private static String trimTrailingPunctuation(String value) {
        return value.replaceFirst("[),.;!?]+$", "");
    }
}
