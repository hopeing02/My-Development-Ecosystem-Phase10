package dev.mde.autoknowledge;

import android.content.Context;
import android.content.SharedPreferences;

final class CaptureSettingsRepository {
    static final String CAPTURE_SOURCE = "capture_source";
    static final String AUTO_CAPTURE_STATE = "auto_capture_state";
    static final String PARENT_DOCUMENT_ID = "parent_document_id";
    static final String PARENT_DOCUMENT_LABEL = "parent_document_label";
    private final SharedPreferences preferences;

    CaptureSettingsRepository(Context context) {
        preferences = context.getSharedPreferences(MainActivity.PREFERENCES, Context.MODE_PRIVATE);
    }

    String serverUrl() {
        return preferences.getString(MainActivity.SERVER_URL, "").trim();
    }

    String targetFolder() {
        return preferences.getString(
                MainActivity.VAULT_FOLDER,
                SharePayload.DEFAULT_VAULT_FOLDER
        );
    }

    CaptureSource source() {
        return CaptureSource.fromStored(preferences.getString(CAPTURE_SOURCE, null));
    }

    void setSource(CaptureSource source) {
        preferences.edit().putString(CAPTURE_SOURCE, source.name()).apply();
    }

    AutoCaptureState state() {
        return AutoCaptureState.fromStored(preferences.getString(AUTO_CAPTURE_STATE, null));
    }

    void setState(AutoCaptureState state) {
        preferences.edit().putString(AUTO_CAPTURE_STATE, state.name()).apply();
    }

    String parentDocumentId() {
        return preferences.getString(PARENT_DOCUMENT_ID, "");
    }

    String parentDocumentLabel() {
        return preferences.getString(PARENT_DOCUMENT_LABEL, "");
    }

    void setParentDocument(String id, String label) {
        preferences.edit()
                .putString(PARENT_DOCUMENT_ID, id)
                .putString(PARENT_DOCUMENT_LABEL, label)
                .apply();
    }

    void clearParentDocument() {
        preferences.edit()
                .remove(PARENT_DOCUMENT_ID)
                .remove(PARENT_DOCUMENT_LABEL)
                .apply();
    }

    boolean canEnableAutoCapture() {
        return !serverUrl().isEmpty() && SharePayload.folderIndex(targetFolder()) >= 0;
    }
}
