package dev.mde.autoknowledge;

interface CaptureRepository {
    CaptureResult saveCapture(CaptureRequest request) throws Exception;
}
