# CODE-006 Android 클립보드 자동 수집

- 구현일: 2026-08-02
- 범위: AutoKnowledge Capture 통합 개발 1단계

## 구현

- 수동 저장과 자동 감지는 `CaptureClipboardTextUseCase`를 공유한다.
- 정규화, 자동 길이·URL 검증, 민감정보 검사, SHA-256, 중복 검사 순서로 처리한다.
- `CaptureRepository`와 `LegacyClipboardCaptureRepository`를 분리해 현재
  `/v1/share`를 사용하면서 다음 단계의 저장소 구현 교체를 허용한다.
- Android 9 포그라운드 서비스가 `OnPrimaryClipChangedListener`를 등록하며,
  종료 시 리스너와 네트워크 콜백을 해제한다.
- 실패 본문은 Android Keystore AES-GCM으로 암호화하여 SharedPreferences 기반
  대기열에 저장한다. 최근 해시는 100건을 유지하고 자동 재시도는 5회로 제한한다.
- 출처, 자동 수집 상태와 상위 문서 선택을 앱 재실행 후 복원한다.

## 보안 경계

화면, 접근성 서비스, OCR, 키보드, 쿠키와 로그인 세션은 읽지 않는다. 클립보드
원문은 로그에 기록하지 않는다.
