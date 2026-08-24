# API-004 Capture API v1

## POST `/api/v1/captures`

요청 Content-Type은 `application/json`이다. 현재 로컬 서버 인증 정책을 유지하며
별도 device-token은 이번 단계에서 추가하지 않는다.

```json
{
  "schemaVersion": "1.0",
  "captureId": "cap_01K...",
  "sourceType": "chatgpt",
  "captureType": "clipboard_item",
  "captureDevice": "android",
  "captureMethod": "android_clipboard",
  "projectId": "autoknowledge-lite",
  "targetFolder": "40_Reference",
  "parentDocument": null,
  "capturedAt": "2026-08-02T21:20:00+09:00",
  "deviceId": "app-generated-random-uuid",
  "contentHash": "64-character-lowercase-sha256",
  "metadata": {"sourceApp": "chatgpt_android"},
  "payload": {
    "content": "복사한 실제 텍스트",
    "title": null,
    "mimeType": "text/plain",
    "language": "ko"
  }
}
```

허용 enum은 `sourceType=chatgpt|codex|general`,
`captureType=clipboard_item|development_session`,
`captureDevice=android|windows`다. clipboard 본문은 정규화 후 UTF-8 1MB까지다.

성공과 본문 중복은 HTTP 200으로 각각 `saved`, `duplicate`를 반환한다. 서버 API는
`queued`를 반환하지 않는다.

```json
{
  "status": "saved",
  "captureId": "cap_01K...",
  "documentId": "doc_or_index_id",
  "documentPath": "40_Reference/2026-08-02-212000-chatgpt-clip-ab12cd34.md",
  "captureType": "clipboard_item",
  "duplicate": false,
  "revision": 1,
  "warnings": []
}
```

오류는 다음 형식이다.

```json
{
  "status": "error",
  "error": {
    "code": "SENSITIVE_CONTENT_DETECTED",
    "message": "민감정보가 감지되어 저장하지 않았습니다.",
    "field": "payload.content"
  },
  "warnings": []
}
```

주요 코드는 `INVALID_SCHEMA_VERSION`, `INVALID_CAPTURE_TYPE`,
`INVALID_SOURCE_TYPE`, `INVALID_CAPTURE_DEVICE`, `INVALID_PAYLOAD`,
`INVALID_TARGET_FOLDER`, `CONTENT_EMPTY`, `CONTENT_TOO_LARGE`,
`SENSITIVE_CONTENT_DETECTED`, `DUPLICATE_CAPTURE_ID`,
`HANDLER_NOT_IMPLEMENTED`, `DOCUMENT_WRITE_FAILED`, `INTERNAL_ERROR`다.
클라이언트 해시 불일치는 저장을 허용하고 `CONTENT_HASH_MISMATCH` warning을
반환한다.

## Legacy `/v1/share`

`capture_origin=android_clipboard`와 `source_type`이 있는 1단계 Android 요청은
Legacy Adapter가 Capture Envelope로 변환해 동일 ClipboardItemHandler를 호출한다.
HTTP 202와 기존 `ShareAccepted` 응답은 유지한다. 범용 PC/API 공유 요청은 기존
AI 처리 흐름을 그대로 사용한다.
