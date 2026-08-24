package dev.mde.autoknowledge;

import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;

final class ClipboardReader {
    private final Context context;
    private final ClipboardManager clipboardManager;

    ClipboardReader(Context context) {
        this.context = context;
        clipboardManager = (ClipboardManager) context.getSystemService(Context.CLIPBOARD_SERVICE);
    }

    CharSequence readText() {
        try {
            ClipData clip = clipboardManager.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) {
                return null;
            }
            ClipData.Item first = clip.getItemAt(0);
            CharSequence direct = first.getText();
            if (direct != null) {
                return direct;
            }
            if (first.getHtmlText() != null) {
                return first.coerceToText(context);
            }
            return null;
        } catch (SecurityException error) {
            return null;
        }
    }

    ClipboardManager manager() {
        return clipboardManager;
    }
}
