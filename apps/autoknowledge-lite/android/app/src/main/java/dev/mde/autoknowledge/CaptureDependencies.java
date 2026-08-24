package dev.mde.autoknowledge;

import android.content.Context;

final class CaptureDependencies {
    final CaptureSettingsRepository settings;
    final AndroidCaptureLocalStore localStore;
    final CaptureClipboardTextUseCase captureUseCase;
    final RetryPendingCapturesUseCase retryUseCase;

    CaptureDependencies(Context context) {
        Context application = context.getApplicationContext();
        settings = new CaptureSettingsRepository(application);
        localStore = new AndroidCaptureLocalStore(application);
        CaptureRepository repository = settings.useLegacyCaptureApi()
                ? new LegacyClipboardCaptureRepository(settings)
                : new UnifiedCaptureRepository(settings, new DefaultCaptureApiRequestMapper());
        captureUseCase = new CaptureClipboardTextUseCase(
                new ClipboardTextNormalizer(),
                new ClipboardCaptureValidator(),
                new SensitiveContentDetector(),
                new ContentHashGenerator(),
                repository,
                localStore
        );
        retryUseCase = new RetryPendingCapturesUseCase(repository, localStore);
    }
}
