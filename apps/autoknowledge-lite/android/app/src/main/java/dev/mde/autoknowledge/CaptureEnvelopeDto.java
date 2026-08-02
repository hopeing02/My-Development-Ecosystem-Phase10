package dev.mde.autoknowledge;

import org.json.JSONException;
import org.json.JSONObject;

final class CaptureEnvelopeDto {
    final String schemaVersion;
    final String captureId;
    final String sourceType;
    final String captureType;
    final String captureDevice;
    final String captureMethod;
    final String projectId;
    final String targetFolder;
    final String parentDocument;
    final String capturedAt;
    final String deviceId;
    final String contentHash;
    final String sourceApp;
    final String title;
    final String content;

    CaptureEnvelopeDto(
            String schemaVersion,
            String captureId,
            String sourceType,
            String captureType,
            String captureDevice,
            String captureMethod,
            String projectId,
            String targetFolder,
            String parentDocument,
            String capturedAt,
            String deviceId,
            String contentHash,
            String sourceApp,
            String title,
            String content
    ) {
        this.schemaVersion = schemaVersion;
        this.captureId = captureId;
        this.sourceType = sourceType;
        this.captureType = captureType;
        this.captureDevice = captureDevice;
        this.captureMethod = captureMethod;
        this.projectId = projectId;
        this.targetFolder = targetFolder;
        this.parentDocument = parentDocument;
        this.capturedAt = capturedAt;
        this.deviceId = deviceId;
        this.contentHash = contentHash;
        this.sourceApp = sourceApp;
        this.title = title;
        this.content = content;
    }

    JSONObject toJson() throws JSONException {
        JSONObject body = new JSONObject()
                .put("schemaVersion", schemaVersion)
                .put("captureId", captureId)
                .put("sourceType", sourceType)
                .put("captureType", captureType)
                .put("captureDevice", captureDevice)
                .put("captureMethod", captureMethod)
                .put("projectId", projectId)
                .put("targetFolder", targetFolder)
                .put("capturedAt", capturedAt)
                .put("deviceId", deviceId)
                .put("contentHash", contentHash)
                .put("metadata", new JSONObject().put("sourceApp", sourceApp))
                .put("payload", new JSONObject()
                        .put("content", content)
                        .put("title", title)
                        .put("mimeType", "text/plain")
                        .put("language", JSONObject.NULL));
        body.put(
                "parentDocument",
                parentDocument == null || parentDocument.isEmpty()
                        ? JSONObject.NULL
                        : parentDocument
        );
        return body;
    }
}
