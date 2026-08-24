# API-009 ChatGPT Search and Timeline

## 목적

로컬에 보존된 ChatGPT 공통 모델을 수정하지 않고 Session, Message, Task, Activity를 관계 정보와 함께 검색하고 시간순으로 조회한다.

## GET `/api/v1/chatgpt/search`

Query:

- `q`: 필수 검색어, 최대 200자
- `entityType`: 선택, `SESSION`, `MESSAGE`, `TASK`, `ACTIVITY`
- `limit`: 1~100, 기본 30

응답 항목은 `entityType`, `entityId`, `title`, `snippet`, `timestamp`, `sessionId`, `sessionTitle`, `taskId`, `messageId`, `provenance`를 포함한다. `sessionId`, `taskId`, `messageId`가 원본 화면으로 이동하는 관계 컨텍스트다.

## GET `/api/v1/chatgpt/timeline`

Query:

- `sessionId`: 선택, 지정하지 않으면 모든 최신 ChatGPT Session
- `limit`: 1~500, 기본 100

응답은 실제 timestamp가 존재하는 Session, Message, Task, Activity만 오름차순으로 반환한다. 누락 timestamp를 임의 생성하지 않으며 `omittedWithoutTimestamp`에 제외 건수를 기록한다.

## Provenance

- 원본 Session과 Message: `source=original`
- 규칙으로 분석한 Task와 Activity: `source=derived`, `derivedBy=rule`

두 API는 읽기 전용이며 원본 archive, projection revision, Markdown을 변경하지 않는다.
