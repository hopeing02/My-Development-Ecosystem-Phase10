package dev.mde.autoknowledge;

final class DefaultCaptureApiRequestMapper implements CaptureApiRequestMapper {
    @Override
    public CaptureEnvelopeDto map(CaptureRequest request) {
        return new CaptureEnvelopeDto(
                "1.0",
                request.captureId,
                request.source.sourceType,
                "clipboard_item",
                "android",
                "android_clipboard",
                "autoknowledge-lite",
                request.targetFolder,
                request.parentDocumentId,
                request.capturedAt,
                request.deviceId,
                request.contentHash,
                request.source.sourceApp,
                request.source.titlePrefix,
                request.content
        );
    }
}
