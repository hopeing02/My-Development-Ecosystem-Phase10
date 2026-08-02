package dev.mde.autoknowledge;

final class CaptureResult {
    final CaptureStatus status;
    final String contentHash;

    CaptureResult(CaptureStatus status, String contentHash) {
        this.status = status;
        this.contentHash = contentHash;
    }
}
