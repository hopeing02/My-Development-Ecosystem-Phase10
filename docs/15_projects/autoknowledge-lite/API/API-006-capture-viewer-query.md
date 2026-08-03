# API-006 Capture Viewer Query API

- 버전: 1.0
- 상태: Implemented

## 목록·상세

- `GET /api/v1/captures`: 검색, 출처·유형·기기·프로젝트·상태·테스트·관계·날짜
  필터, 정렬과 cursor pagination
- `GET /api/v1/captures/{captureId}`: 유형별 개요와 하위 자료 count
- `PATCH /api/v1/captures/{captureId}`: 제목, 태그, 프로젝트, 상위 주제, 사용자 메모

## 지연 조회

- `GET /api/v1/captures/{captureId}/messages`
- `GET /api/v1/captures/{captureId}/commands`
- `GET /api/v1/captures/{captureId}/changed-files`
- `GET /api/v1/captures/{captureId}/tests`
- `GET /api/v1/captures/{captureId}/diffs`
- `GET /api/v1/captures/{captureId}/attachments`
- `GET /api/v1/files/history?path=...`
- `GET /api/v1/documents/{documentId}/capture-backlinks`

## 그래프

- `GET /api/v1/graph`
- `GET /api/v1/graph/neighborhood/{entityId}`

`depth`는 1~4, `limit`는 최대 300이다. `includeCandidates=false`가 기본이며
`nodeTypes`, `relationTypes`, `projectId`, `testStatus`, `sourceType` 필터를 지원한다.

## 오류

`CAPTURE_NOT_FOUND`, `CAPTURE_DETAIL_LOAD_FAILED`, `INVALID_CURSOR`,
`GRAPH_NODE_NOT_FOUND`, `CAPTURE_SERVICE_UNAVAILABLE`를 사용한다. 개별 탭 오류는
해당 탭에서 재시도하며 상세 개요를 제거하지 않는다.

