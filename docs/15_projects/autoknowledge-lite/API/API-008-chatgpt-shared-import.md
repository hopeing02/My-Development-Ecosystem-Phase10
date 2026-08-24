# API-008 ChatGPT Shared Link Import

## Endpoint

```text
POST /api/v1/chatgpt/shared-imports
Content-Type: application/json
Authorization: Bearer {AUTOKNOWLEDGE_CONTROL_API_KEY}

{"url":"https://chatgpt.com/share/<conversation-ID>"}
```

호출은 사용자가 공개 Shared Link 1건을 명시적으로 제출한 경우에만 수행한다. 서버는
ChatGPT account credential이나 cookie를 사용하지 않는다.

## 성공 응답

Export Import와 같은 안전한 요약 형식을 사용한다.

```json
{
  "status": "imported",
  "importId": "chatgpt_shared_...",
  "rawDuplicate": false,
  "discoveredSessions": 1,
  "projectedSessions": 1,
  "duplicateSessions": 0,
  "failedSessions": 0,
  "warnings": []
}
```

손상 snapshot을 raw Archive에는 보존했지만 투영할 수 없으면 HTTP 200과
`status=partial`, warning code를 반환한다. 응답에 Shared URL, 원문과 raw path를
포함하지 않는다.

## 오류

- `401`: Bearer token 누락 또는 불일치
- `413`: request 또는 remote snapshot 크기 제한 초과
- `415`: request 또는 remote response content type 미지원
- `422`: request 또는 canonical Shared Link URL 오류
- `502`: ChatGPT Shared Link upstream 조회 실패
- `503`: Import API 미설정 또는 local Archive 실패
