package dev.mde.autoknowledge;

import android.content.Context;
import android.content.SharedPreferences;

final class CaptureSettingsRepository {
    static final String CAPTURE_SOURCE = "capture_source";
    static final String AUTO_CAPTURE_STATE = "auto_capture_state";
    static final String PARENT_DOCUMENT_ID = "parent_document_id";
    static final String PARENT_DOCUMENT_LABEL = "parent_document_label";
    static final String USE_LEGACY_CAPTURE_API = "use_legacy_capture_api";
    static final String CONTROL_API_KEY = "control_api_key";
    static final String CODEX_CAPTURE_SESSION_ID = "codex_capture_session_id";
    static final String KNOWLEDGE_VIEWER_URL = "knowledge_viewer_url";
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

    boolean useLegacyCaptureApi() {
        return preferences.getBoolean(USE_LEGACY_CAPTURE_API, false);
    }

    void setUseLegacyCaptureApi(boolean enabled) {
        preferences.edit().putBoolean(USE_LEGACY_CAPTURE_API, enabled).apply();
    }

    String controlApiKey() {
        return preferences.getString(CONTROL_API_KEY, "");
    }

    void setControlApiKey(String value) {
        preferences.edit().putString(CONTROL_API_KEY, value).apply();
    }

    String codexCaptureSessionId() {
        return preferences.getString(CODEX_CAPTURE_SESSION_ID, "");
    }

    void setCodexCaptureSessionId(String value) {
        preferences.edit().putString(CODEX_CAPTURE_SESSION_ID, value).apply();
    }

    String knowledgeViewerUrl() {
        return preferences.getString(KNOWLEDGE_VIEWER_URL, "");
    }

    void setKnowledgeViewerUrl(String value) {
        preferences.edit().putString(KNOWLEDGE_VIEWER_URL, value).apply();
    }
}
