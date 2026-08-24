package dev.mde.autoknowledge;

import org.json.JSONObject;

final class CodexProject {
    final String projectId;
    final String displayName;

    CodexProject(String projectId, String displayName) {
        this.projectId = projectId;
        this.displayName = displayName;
    }

    static CodexProject fromJson(JSONObject value) {
        return new CodexProject(
                value.optString("projectId"),
                value.optString("displayName", value.optString("projectId"))
        );
    }

    @Override
    public String toString() {
        return displayName;
    }
}
