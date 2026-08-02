package dev.mde.autoknowledge;

import java.time.OffsetDateTime;

final class CaptureRequest {
    final CaptureSource source;
    final String content;
    final String contentHash;
    final String targetFolder;
    final String parentDocumentId;
    final String capturedAt;
    final String deviceId;

    CaptureRequest(
            CaptureSource source,
            String content,
            String contentHash,
            String targetFolder,
            String parentDocumentId,
            String capturedAt,
            String deviceId
    ) {
        this.source = source;
        this.content = content;
        this.contentHash = contentHash;
        this.targetFolder = targetFolder;
        this.parentDocumentId = parentDocumentId == null ? "" : parentDocumentId;
        this.capturedAt = capturedAt;
        this.deviceId = deviceId;
    }

    static CaptureRequest now(
            CaptureSource source,
            String content,
            String contentHash,
            String targetFolder,
            String parentDocumentId,
            String deviceId
    ) {
        return new CaptureRequest(
                source,
                content,
                contentHash,
                targetFolder,
                parentDocumentId,
                OffsetDateTime.now().toString(),
                deviceId
        );
    }
}
