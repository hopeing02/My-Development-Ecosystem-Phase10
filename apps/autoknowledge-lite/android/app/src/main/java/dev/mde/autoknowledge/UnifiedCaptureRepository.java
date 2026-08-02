package dev.mde.autoknowledge;

import java.util.function.Supplier;

final class UnifiedCaptureRepository implements CaptureRepository {
    private final Supplier<String> serverUrlProvider;
    private final CaptureApiRequestMapper mapper;

    UnifiedCaptureRepository(
            CaptureSettingsRepository settings,
            CaptureApiRequestMapper mapper
    ) {
        this(settings::serverUrl, mapper);
    }

    UnifiedCaptureRepository(
            Supplier<String> serverUrlProvider,
            CaptureApiRequestMapper mapper
    ) {
        this.serverUrlProvider = serverUrlProvider;
        this.mapper = mapper;
    }

    @Override
    public CaptureResult saveCapture(CaptureRequest request) throws Exception {
        String serverUrl = serverUrlProvider.get();
        if (serverUrl.isEmpty()) {
            throw new IllegalStateException("Server URL is missing");
        }
        return ApiClient.submitCapture(serverUrl, mapper.map(request), request.contentHash);
    }
}
