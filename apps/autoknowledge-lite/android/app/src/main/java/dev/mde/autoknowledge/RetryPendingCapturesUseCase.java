package dev.mde.autoknowledge;

final class RetryPendingCapturesUseCase {
    static final int MAX_AUTO_RETRIES = 5;
    private final CaptureRepository captureRepository;
    private final CaptureLocalStore localStore;

    RetryPendingCapturesUseCase(CaptureRepository captureRepository, CaptureLocalStore localStore) {
        this.captureRepository = captureRepository;
        this.localStore = localStore;
    }

    int execute(boolean manual) {
        int saved = 0;
        for (CaptureRequest request : localStore.pending()) {
            if (!manual && localStore.retryCount(request.contentHash) >= MAX_AUTO_RETRIES) {
                continue;
            }
            try {
                CaptureResult result = captureRepository.saveCapture(request);
                if (result.status == CaptureStatus.SAVED || result.status == CaptureStatus.DUPLICATE) {
                    localStore.removePending(request.contentHash);
                    localStore.recordHash(request.contentHash);
                    saved++;
                } else if (result.status == CaptureStatus.FAILED
                        || result.status == CaptureStatus.BLOCKED_SENSITIVE) {
                    localStore.markPermanentFailure(request.contentHash);
                }
            } catch (Exception error) {
                localStore.markRetryFailed(request.contentHash);
            }
        }
        return saved;
    }
}
