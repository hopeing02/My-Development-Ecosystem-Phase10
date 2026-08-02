# CODE-007 공통 Capture 모델과 통합 저장 API

- 구현일: 2026-08-02
- 범위: AutoKnowledge Capture 통합 개발 2단계

## 서버

- `capture_api.py`에 버전 모델, Handler Protocol/Registry, Application Service,
  Clipboard renderer, 파일 기반 멱등 인덱스와 FastAPI 라우트를 분리했다.
- 서버 정규화 결과의 SHA-256을 중복 기준으로 사용하고 클라이언트 해시는
  warning 검증에만 사용한다.
- 저장은 임시 파일과 `os.replace`를 사용하며 색인 실패 시 Markdown을 유지한다.
- `/v1/share`의 Android 클립보드 요청은 Legacy Adapter를 통과한다.

## Android

- `UnifiedCaptureRepository`, `CaptureApiRequestMapper`, `CaptureEnvelopeDto`를
  추가했다.
- `CaptureDependencies`의 기본 구현만 통합 저장소로 바꾸고 UseCase, 서비스와 UI는
  변경하지 않았다.
- `use_legacy_capture_api=true` 설정으로 기존 저장소에 롤백할 수 있다.
- 기존 큐는 읽을 때 captureId를 보강하며 해독 또는 변환 실패 항목은 삭제하지
  않고 `MIGRATION_FAILED`로 표시한다.

## 공통 자산

JSON Schema와 normalization, sensitive-content, hashes, filenames 테스트 벡터를
`packages/capture-core/`에 두었다.
