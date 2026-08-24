package dev.mde.autoknowledge;

final class LegacyClipboardCaptureRepository implements CaptureRepository {
    private final CaptureSettingsRepository settings;

    LegacyClipboardCaptureRepository(CaptureSettingsRepository settings) {
        this.settings = settings;
    }

    @Override
    public CaptureResult saveCapture(CaptureRequest request) throws Exception {
        String serverUrl = settings.serverUrl();
        if (serverUrl.isEmpty()) {
            throw new IllegalStateException("Server URL is missing");
        }
        ApiClient.submit(serverUrl, SharePayload.fromCapture(request));
        return new CaptureResult(CaptureStatus.SAVED, request.contentHash);
    }
}
