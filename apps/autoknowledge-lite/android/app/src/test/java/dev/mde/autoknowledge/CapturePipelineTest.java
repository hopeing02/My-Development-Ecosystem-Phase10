package dev.mde.autoknowledge;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

public final class CapturePipelineTest {
    @Test
    public void normalizesLineEndingsAndWhitespaceWithoutChangingCodeIndentation() {
        ClipboardTextNormalizer normalizer = new ClipboardTextNormalizer();

        String normalized = normalizer.normalize(
                "  한글 원문  \r\n\r\n\r\n\r\n```java\r\n  value  \r\n```  "
        );

        assertEquals("한글 원문\n\n\n```java\n  value  \n```", normalized);
    }

    @Test
    public void validatesAutomaticAndManualCaptureRules() {
        ClipboardCaptureValidator validator = new ClipboardCaptureValidator();

        assertFalse(validator.isValid(null, true));
        assertFalse(validator.isValid("   ", true));
        assertFalse(validator.isValid("짧은 글", true));
        assertTrue(validator.isValid("짧은 글", false));
        assertFalse(validator.isValid("https://example.com/page", true));
        assertTrue(validator.isValid(
                "아래 문서를 참고하세요. https://example.com/page 이 문서는 충분히 긴 본문입니다.",
                true
        ));
    }

    @Test
    public void detectsConcreteSecretsButAllowsExplanatoryWords() {
        SensitiveContentDetector detector = new SensitiveContentDetector();

        assertTrue(detector.containsSensitiveContent("Authorization: Bearer abcdefghijklmnop"));
        assertTrue(detector.containsSensitiveContent("OPENAI_API_KEY=sk-abcdefghijklmnop"));
        assertTrue(detector.containsSensitiveContent("-----BEGIN PRIVATE KEY-----"));
        assertTrue(detector.containsSensitiveContent("482913"));
        assertFalse(detector.containsSensitiveContent(
                "이 문서는 token과 password라는 개념을 일반적으로 설명합니다."
        ));
    }

    @Test
    public void hashUsesNormalizedContentAndDoesNotIncludeSource() {
        ClipboardTextNormalizer normalizer = new ClipboardTextNormalizer();
        ContentHashGenerator generator = new ContentHashGenerator();

        String first = generator.sha256(normalizer.normalize("첫 줄\r\n둘째 줄"));
        String second = generator.sha256(normalizer.normalize("첫 줄\n둘째 줄"));
        String different = generator.sha256(normalizer.normalize("다른 본문"));

        assertEquals(first, second);
        assertNotEquals(first, different);
    }

    @Test
    public void pipelineDeduplicatesAcrossSourcesAndQueuesNetworkFailures() {
        FakeLocalStore store = new FakeLocalStore();
        FakeRepository repository = new FakeRepository();
        CaptureClipboardTextUseCase useCase = useCase(repository, store);
        String content = "서른 글자를 넘는 동일한 본문을 출처만 바꾸어 두 번 저장하는 테스트 문장입니다.";

        CaptureResult saved = useCase.execute(
                content, true, CaptureSource.CHATGPT, "40_Reference", "", "device"
        );
        CaptureResult duplicate = useCase.execute(
                content, true, CaptureSource.CODEX, "40_Reference", "", "device"
        );
        repository.fail = true;
        CaptureResult queued = useCase.execute(
                content + " 새로운 내용", true, CaptureSource.GENERAL,
                "40_Reference", "", "device"
        );

        assertEquals(CaptureStatus.SAVED, saved.status);
        assertEquals(CaptureStatus.DUPLICATE, duplicate.status);
        assertEquals(CaptureStatus.QUEUED, queued.status);
        assertEquals(1, store.pendingCount());
    }

    private static CaptureClipboardTextUseCase useCase(
            CaptureRepository repository,
            CaptureLocalStore store
    ) {
        return new CaptureClipboardTextUseCase(
                new ClipboardTextNormalizer(),
                new ClipboardCaptureValidator(),
                new SensitiveContentDetector(),
                new ContentHashGenerator(),
                repository,
                store
        );
    }

    private static final class FakeRepository implements CaptureRepository {
        boolean fail;

        @Override
        public CaptureResult saveCapture(CaptureRequest request) throws Exception {
            if (fail) {
                throw new Exception("offline");
            }
            return new CaptureResult(CaptureStatus.SAVED, request.contentHash);
        }
    }

    private static final class FakeLocalStore implements CaptureLocalStore {
        final Set<String> hashes = new LinkedHashSet<>();
        final List<CaptureRequest> pending = new ArrayList<>();

        @Override
        public boolean containsHash(String hash) {
            if (hashes.contains(hash)) {
                return true;
            }
            for (CaptureRequest request : pending) {
                if (request.contentHash.equals(hash)) {
                    return true;
                }
            }
            return false;
        }

        @Override
        public void recordHash(String hash) {
            hashes.add(hash);
            while (hashes.size() > 100) {
                hashes.remove(hashes.iterator().next());
            }
        }

        @Override
        public void enqueue(CaptureRequest request) {
            pending.add(request);
        }

        @Override
        public List<CaptureRequest> pending() {
            return new ArrayList<>(pending);
        }

        @Override
        public int retryCount(String hash) {
            return 0;
        }

        @Override
        public void markRetryFailed(String hash) {}

        @Override
        public void removePending(String hash) {
            pending.removeIf(request -> request.contentHash.equals(hash));
        }

        @Override
        public int pendingCount() {
            return pending.size();
        }
    }
}
