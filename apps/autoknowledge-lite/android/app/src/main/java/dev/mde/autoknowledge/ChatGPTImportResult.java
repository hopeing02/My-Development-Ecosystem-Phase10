package dev.mde.autoknowledge;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

final class ChatGPTImportResult {
    final String status;
    final int discoveredSessions;
    final int projectedSessions;
    final int duplicateSessions;
    final int failedSessions;
    final int warningCount;

    private ChatGPTImportResult(
            String status,
            int discoveredSessions,
            int projectedSessions,
            int duplicateSessions,
            int failedSessions,
            int warningCount
    ) {
        this.status = status;
        this.discoveredSessions = discoveredSessions;
        this.projectedSessions = projectedSessions;
        this.duplicateSessions = duplicateSessions;
        this.failedSessions = failedSessions;
        this.warningCount = warningCount;
    }

    static ChatGPTImportResult fromJson(JSONObject value) throws JSONException {
        String status = value.getString("status");
        if (!status.equals("imported")
                && !status.equals("partial")
                && !status.equals("duplicate")) {
            throw new JSONException("Unsupported ChatGPT import status");
        }
        JSONArray warnings = value.optJSONArray("warnings");
        return new ChatGPTImportResult(
                status,
                value.getInt("discoveredSessions"),
                value.getInt("projectedSessions"),
                value.getInt("duplicateSessions"),
                value.getInt("failedSessions"),
                warnings == null ? 0 : warnings.length()
        );
    }

    String label() {
        String state;
        if (status.equals("partial")) {
            state = "일부 세션 가져오기 완료";
        } else if (status.equals("duplicate")) {
            state = "이미 가져온 원본";
        } else {
            state = "가져오기 완료";
        }
        return state
                + " · 발견 " + discoveredSessions
                + " · 신규 " + projectedSessions
                + " · 중복 " + duplicateSessions
                + " · 실패 " + failedSessions
                + (warningCount > 0 ? " · 경고 " + warningCount : "");
    }
}
