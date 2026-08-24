package dev.mde.autoknowledge;

import java.util.List;
import java.util.regex.Pattern;

final class SensitiveContentDetector {
    private static final List<Pattern> PATTERNS = List.of(
            Pattern.compile("(?i)\\b(?:sk|ghp|gho|github_pat)-?[A-Za-z0-9_\\-]{16,}\\b"),
            Pattern.compile("(?i)authorization\\s*:\\s*bearer\\s+\\S+"),
            Pattern.compile("(?i)\\bbearer\\s+[A-Za-z0-9._~+/=-]{12,}"),
            Pattern.compile("(?i)\\b(?:password|passwd|secret|api[_-]?key|oauth[_-]?token|access[_-]?token)\\s*[:=]\\s*[^\\s]{6,}"),
            Pattern.compile("-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            Pattern.compile("(?<!\\d)\\d{6}-?[1-4]\\d{6}(?!\\d)"),
            Pattern.compile("(?<!\\d)(?:\\d[ -]?){15}\\d(?!\\d)")
    );

    boolean containsSensitiveContent(String text) {
        if (text == null) {
            return false;
        }
        String trimmed = text.trim();
        if (trimmed.length() <= 12 && trimmed.matches("\\d{4,8}")) {
            return true;
        }
        for (Pattern pattern : PATTERNS) {
            if (pattern.matcher(text).find()) {
                return true;
            }
        }
        return false;
    }
}
