# API-007 ChatGPT Export Import

## Endpoint

```text
POST /api/v1/chatgpt/imports
Content-Type: application/zip
Authorization: Bearer {AUTOKNOWLEDGE_CONTROL_API_KEY}
X-File-Name: chatgpt-export.zip
```

Request body는 ChatGPT Data Export ZIP binary다. `application/octet-stream`도
허용한다. multipart form은 사용하지 않는다.

## 성공 응답

```json
{
  "status": "imported",
  "importId": "chatgpt_...",
  "rawDuplicate": false,
  "discoveredSessions": 10,
  "projectedSessions": 9,
  "duplicateSessions": 0,
  "failedSessions": 1,
  "warnings": []
}
```

`status`는 `imported`, `partial`, `duplicate` 중 하나다. 원문과 raw Archive 경로는
응답에 포함하지 않는다.

## 오류

- `401`: Bearer token 누락 또는 불일치
- `409`: 기존 Archive/projection 무결성 충돌
- `413`: upload 또는 Archive 크기 제한 초과
- `415`: 지원하지 않는 Content-Type
- `422`: ZIP 또는 conversations JSON 형식 오류
- `503`: Import API 미설정 또는 로컬 저장 실패
