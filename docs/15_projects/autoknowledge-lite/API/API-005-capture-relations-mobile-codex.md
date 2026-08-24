# API-005 Capture 관계와 모바일 Codex 제어 API

## 인증

`AUTOKNOWLEDGE_CONTROL_API_KEY`를 설정한 뒤 모바일 제어 및 관계 변경 요청에 `Authorization: Bearer <key>`를 보낸다. 키가 없는 모바일 제어 API는 `CONTROL_API_DISABLED`로 503을 반환한다. 응답에는 키, 사용자 경로와 대화 원문이 포함되지 않는다.

## 관계 API

- `GET /api/v1/captures/{captureId}/relation-candidates`
- `POST /api/v1/captures/{captureId}/relation-candidates/search`
- `GET /api/v1/captures/{captureId}/relations`
- `GET /api/v1/captures/{sessionCaptureId}/excerpts`
- `POST /api/v1/capture-relations`
- `POST /api/v1/capture-relations/{relationId}/confirm`
- `POST /api/v1/capture-relations/{relationId}/reject`
- `DELETE /api/v1/capture-relations/{relationId}`

조회 필터는 `relationType=excerpt_of`, `status`, `direction=both|in|out`이다. 변경 API는 설정된 제어 키가 있으면 같은 인증을 요구한다.

## 모바일 Codex API

- `GET /api/v1/mobile/status`
- `GET /api/v1/mobile/codex/projects`
- `GET /api/v1/mobile/codex/sessions?limit=20`
- `GET /api/v1/mobile/codex/sessions/{sourceSessionId}`
- `POST /api/v1/mobile/codex/captures`
- `POST /api/v1/mobile/codex/captures/{captureSessionId}/attach`
- `POST /api/v1/mobile/codex/captures/{captureSessionId}/sync`
- `POST /api/v1/mobile/codex/captures/{captureSessionId}/finalize`
- `GET /api/v1/mobile/codex/captures/{captureSessionId}`

attach 본문의 `consent`는 반드시 `true`다. 프로젝트는 PC에 이미 등록된 ID만 선택할 수 있고 API로 등록·경로 변경·명령 실행은 할 수 없다.

저장 상태 응답의 `viewerUrl`은 문서 ID가 있으면 `sourceId`와 `documentId` 딥링크를 포함한다. Viewer는 해당 문서를 바로 열되 민감 Source 확인 정책을 우회하지 않는다.

## 실행 설정

```powershell
$env:AUTOKNOWLEDGE_CONTROL_API_KEY='<random-device-secret>'
$env:AUTOKNOWLEDGE_VIEWER_URL='http://100.75.235.67:8765'
$env:MDE_CODEX_CONVERSATION_CAPTURE='1'
```
