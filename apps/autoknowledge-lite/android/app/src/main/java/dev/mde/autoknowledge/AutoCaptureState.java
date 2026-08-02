package dev.mde.autoknowledge;

enum AutoCaptureState {
    DISABLED,
    RUNNING,
    PAUSED,
    ERROR;

    static AutoCaptureState fromStored(String value) {
        try {
            return valueOf(value);
        } catch (IllegalArgumentException | NullPointerException error) {
            return DISABLED;
        }
    }
}
