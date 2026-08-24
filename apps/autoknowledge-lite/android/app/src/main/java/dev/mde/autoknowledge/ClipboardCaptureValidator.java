package dev.mde.autoknowledge;

import java.util.regex.Pattern;

final class ClipboardCaptureValidator {
    static final int MIN_AUTO_CAPTURE_LENGTH = 30;
    private static final Pattern URL_ONLY = Pattern.compile("(?i)^https?://\\S+$");

    boolean isValid(String text, boolean automatic) {
        if (text == null || text.trim().isEmpty()) {
            return false;
        }
        if (!automatic) {
            return true;
        }
        return text.length() >= MIN_AUTO_CAPTURE_LENGTH && !URL_ONLY.matcher(text.trim()).matches();
    }
}
