# SDS-005 공통 Capture 모델과 통합 저장 API

- 버전: 1.0
- 상태: Implemented

## 구성

```text
CaptureEnvelope
  -> CaptureApplicationService
  -> CaptureHandlerRegistry
     -> ClipboardItemHandler
     -> DevelopmentSessionHandler
```

공통 Envelope의 필수 필드는 `schemaVersion`, `captureId`, `sourceType`,
`captureType`, `captureDevice`, `captureMethod`, `projectId`, `targetFolder`,
`parentDocument`, `capturedAt`, `deviceId`, `contentHash`, `metadata`, `payload`다.
정식 기계 판독 계약은
`packages/capture-core/schemas/capture-envelope-v1.schema.json`이다.

## Clipboard 처리

서버는 본문 정규화, 1MB 제한, 민감정보 차단, 서버 해시 계산, captureId 멱등성,
본문 중복, Markdown 렌더링, 원자 저장, MDE 단일 파일 색인과 상위 문서 연결 순서로
처리한다. 색인 또는 연결 실패는 저장 문서를 삭제하지 않고 warning으로 반환한다.

## 저장 경계

`targetFolder`는 ADR-012 allowlist만 허용한다. 실제 경로를 resolve한 뒤 Vault
루트 하위인지 확인하므로 허용 폴더가 심볼릭 링크로 외부를 가리켜도 차단한다.
파일명은 `YYYY-MM-DD-HHmmss-{source}-clip-{hash8}.md`다.

## Android 전환

`CaptureRequest -> CaptureApiRequestMapper -> CaptureEnvelopeDto`로 변환한다.
5xx와 네트워크 오류만 예외로 전달해 기존 UseCase가 대기열에 넣고, 4xx는
`FAILED` 또는 `BLOCKED_SENSITIVE`로 끝낸다. 기존 큐에 captureId가 없으면
`cap_legacy_{contentHash}`로 안정적으로 보강한다.
