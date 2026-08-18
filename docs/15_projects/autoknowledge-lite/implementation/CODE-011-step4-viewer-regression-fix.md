# CODE-011 Step 4 Viewer 회귀 보완

- 작성일: 2026-08-18
- 상태: Complete

## 범위

Step 5 시작 전에 기존 Knowledge Viewer의 Codex 개발 세션 개요, 대화, 변경 파일,
명령, 테스트와 Capture Graph를 실제 자료가 있는 fixture와 자료가 없는 fixture로
검증했다.

## 변경

- 원본 증거가 하나 이상 존재하는 세션에 안정적인 session 범위 Task 후보를 투영
- Task는 `boundaryStatus=suggested`, `derivedBy=rule`, confidence 0.5로 표시
- 기존 Session→File/Command/Test 노드와 Edge를 보존
- `Session → Task`, `Task → File/Command/Test` 관계를 추가
- 각 Session 탭에서 관련 Task 상세로 이동
- Task 상세에서 세션 개요·원본 대화·파일·명령·테스트로 복귀
- Task 상세에서 Task 중심 그래프로 이동
- 자료가 없는 탭과 관계가 없는 그래프에 명확한 empty state 표시
- 원본 Capture payload와 Session Markdown은 변경하지 않음

## 호환성

기존 Query 응답에는 optional `tasks`와 `taskId`만 추가했다. 기존 Capture Graph
노드와 Edge는 삭제하거나 이름을 변경하지 않았다. 빈 세션에는 근거 없는 Task를
생성하지 않는다. 이 Task는 향후 자동 Task 분류 결과가 아니라 Step 4 자료를 연결하기
위한 단일 session 범위 후보이다.
