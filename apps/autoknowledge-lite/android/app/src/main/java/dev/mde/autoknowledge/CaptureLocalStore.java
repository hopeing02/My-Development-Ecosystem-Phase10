package dev.mde.autoknowledge;

import java.util.List;

interface CaptureLocalStore {
    boolean containsHash(String hash);

    void recordHash(String hash);

    void enqueue(CaptureRequest request) throws Exception;

    List<CaptureRequest> pending();

    int retryCount(String hash);

    void markRetryFailed(String hash);

    void removePending(String hash);

    int pendingCount();
}
