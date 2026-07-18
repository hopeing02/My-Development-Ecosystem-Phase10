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

    boolean isValid() {
        return !content.trim().isEmpty();
    }

    private static String trimTrailingPunctuation(String value) {
        return value.replaceFirst("[),.;!?]+$", "");
    }
}
