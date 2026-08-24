package dev.mde.autoknowledge;

import java.net.URI;
import java.net.URISyntaxException;
import java.util.regex.Pattern;

final class ChatGPTSharedLinkValidator {
    private static final Pattern PATH = Pattern.compile(
            "^/share/[A-Za-z0-9_-]{8,128}/?$"
    );

    private ChatGPTSharedLinkValidator() {}

    static String validate(String rawValue) {
        String value = sanitizeCopiedValue(rawValue);
        try {
            URI uri = new URI(value);
            String path = uri.getPath();
            if (!"https".equalsIgnoreCase(uri.getScheme())
                    || !"chatgpt.com".equalsIgnoreCase(uri.getHost())
                    || uri.getPort() != -1 && uri.getPort() != 443
                    || uri.getRawUserInfo() != null
                    || path == null
                    || !PATH.matcher(path).matches()) {
                throw new IllegalArgumentException("공식 ChatGPT Shared Link 형식이 아닙니다.");
            }
            if (path.endsWith("/")) {
                path = path.substring(0, path.length() - 1);
            }
            return "https://chatgpt.com" + path;
        } catch (URISyntaxException error) {
            throw new IllegalArgumentException("공식 ChatGPT Shared Link 형식이 아닙니다.");
        }
    }

    private static String sanitizeCopiedValue(String rawValue) {
        String value = rawValue == null ? "" : rawValue.trim();
        return value
                .replace("\u200B", "")
                .replace("\u200C", "")
                .replace("\u200D", "")
                .replace("\u2060", "")
                .replace("\uFEFF", "");
    }
}
