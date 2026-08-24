# CODE-029 Task/Activity Knowledge Graph 통합

- 작성일: 2026-08-19
- 상태: Complete

## 목적

Step 6에서 파생한 ChatGPT Task와 Activity를 기존 Knowledge Graph 조회에 추가해 원본 Message까지 추적할 수 있게 한다. 기존 Capture, Document 및 Codex 그래프를 제거하거나 교체하지 않는다.

## 노드

- `CHATGPT_SESSION`
- `CHATGPT_MESSAGE`
- `TASK`
- `ACTIVITY`

Task와 Activity 노드에는 식별자, 상태, 유형, sequence 및 provenance 추적에 필요한 최소 metadata만 포함한다. 원본 Message content는 graph metadata에 복제하지 않는다.

## 관계

- Session `contains_message` Message
- Session `contains_task` Task
- Task `contains_activity` Activity
- Activity `derived_from` Message

Task 경계의 `suggested` 상태는 관계에 유지하며 Viewer에서 점선으로 구분한다. Activity와 원본 Message의 식별 연결은 `confirmed` 관계다.

## 기존 그래프 통합

`CaptureQueryService`에 선택적 graph provider를 주입해 기존 `/api/v1/graph`와 `/api/v1/graph/neighborhood/{id}` 응답에 ChatGPT graph를 병합한다.

- 기존 Capture/Document/Codex 노드 생성 로직 유지
- `projectId` 또는 `testStatus` 필터에서는 관련 없는 ChatGPT graph 제외
- `sourceType=codex` 필터에서는 ChatGPT graph 제외
- nodeTypes와 relationTypes 필터 재사용
- ChatGPT projection 오류는 기존 그래프 실패로 전파하지 않고 `CHATGPT_GRAPH_UNAVAILABLE` warning으로 격리
- 최종 node limit과 dangling edge 제거 로직 재사용

## Viewer

기존 Cytoscape 컴포넌트에 `ACTIVITY` 색상과 관계 이름을 추가했다. ChatGPT Task 및 Activity를 선택하면 원본 ChatGPT Session으로 이동하며 기존 Capture Task 선택 동작은 유지한다.

