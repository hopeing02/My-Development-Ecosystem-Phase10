# ADR-017 AutoKnowledge 공통 Capture API

- 상태: Accepted
- 결정일: 2026-08-02

## 배경

Android 클립보드 수집은 `/v1/share`의 제품별 필드에 의존했다. Windows Codex
수집기를 추가하기 전에 플랫폼과 저장 처리를 분리하고, captureId 멱등성과 본문
중복을 서버 기준으로 일관되게 처리할 계약이 필요하다.

## 결정

- 모든 신규 수집기는 Schema `1.0` Capture Envelope를 `POST /api/v1/captures`로
  보낸다.
- Envelope는 공통 메타데이터와 유형별 payload를 분리한다.
- `CaptureHandlerRegistry`가 `clipboard_item`과 `development_session` Handler를
  선택한다.
- `clipboard_item`은 서버가 정규화·민감정보 검사·SHA-256·중복 검사를 다시
  수행하고 Markdown을 원자 저장한다.
- `development_session`은 계약을 검증한 뒤 `HANDLER_NOT_IMPLEMENTED`를 반환하며
  3단계 전에는 저장하지 않는다.
- captureId 인덱스는 기존 파일 기반 런타임 경계 안에 원자 저장하고 별도 DB를
  도입하지 않는다.
- 기존 `/v1/share` Android 요청은 Legacy Adapter로 공통 Handler에 연결한다.
- Android는 기본적으로 `UnifiedCaptureRepository`를 사용하며 설정 플래그로
  `LegacyClipboardCaptureRepository`에 롤백할 수 있다.

## 결과

서버 API의 상태는 `saved`, `duplicate`, `error`만 사용한다. 네트워크 장애의
`QUEUED`와 변환 실패의 `MIGRATION_FAILED`는 Android 로컬 상태로 남는다. 동일
본문은 출처와 무관하게 중복이며, 동일 captureId의 다른 요청은 충돌이다.

## 제외 범위

Windows 수집기, development_session 저장, AI 요약, Viewer 변경, 인증 체계 개편은
이번 결정에 포함하지 않는다.
