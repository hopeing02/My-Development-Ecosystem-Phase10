package dev.mde.autoknowledge;

import java.util.HashSet;
import java.util.Set;

final class CaptureClipboardTextUseCase {
    private final ClipboardTextNormalizer normalizer;
    private final ClipboardCaptureValidator validator;
    private final SensitiveContentDetector sensitiveContentDetector;
    private final ContentHashGenerator hashGenerator;
    private final CaptureRepository captureRepository;
    private final CaptureLocalStore localStore;
    private final Set<String> inFlight = new HashSet<>();

    CaptureClipboardTextUseCase(
            ClipboardTextNormalizer normalizer,
            ClipboardCaptureValidator validator,
            SensitiveContentDetector sensitiveContentDetector,
            ContentHashGenerator hashGenerator,
            CaptureRepository captureRepository,
            CaptureLocalStore localStore
    ) {
        this.normalizer = normalizer;
        this.validator = validator;
        this.sensitiveContentDetector = sensitiveContentDetector;
        this.hashGenerator = hashGenerator;
        this.captureRepository = captureRepository;
        this.localStore = localStore;
    }

    CaptureResult execute(
            CharSequence rawText,
            boolean automatic,
            CaptureSource source,
            String targetFolder,
            String parentDocumentId,
            String deviceId
    ) {
        String content = normalizer.normalize(rawText);
        if (!validator.isValid(content, automatic)) {
            return new CaptureResult(CaptureStatus.SKIPPED, "");
        }
        if (sensitiveContentDetector.containsSensitiveContent(content)) {
            return new CaptureResult(CaptureStatus.BLOCKED_SENSITIVE, "");
        }
        String hash = hashGenerator.sha256(content);
        synchronized (inFlight) {
            if (inFlight.contains(hash) || localStore.containsHash(hash)) {
                return new CaptureResult(CaptureStatus.DUPLICATE, hash);
            }
            inFlight.add(hash);
        }
        CaptureRequest request = CaptureRequest.now(
                source,
                content,
                hash,
                targetFolder,
                parentDocumentId,
                deviceId
        );
        try {
            CaptureResult result = captureRepository.saveCapture(request);
            if (result.status == CaptureStatus.SAVED || result.status == CaptureStatus.DUPLICATE) {
                localStore.recordHash(hash);
            }
            return result;
        } catch (Exception networkError) {
            try {
                localStore.enqueue(request);
                return new CaptureResult(CaptureStatus.QUEUED, hash);
            } catch (Exception storageError) {
                return new CaptureResult(CaptureStatus.FAILED, hash);
            }
        } finally {
            synchronized (inFlight) {
                inFlight.remove(hash);
            }
        }
    }
}
