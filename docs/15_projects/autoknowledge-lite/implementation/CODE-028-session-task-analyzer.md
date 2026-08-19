# CODE-028 Session Task 분석기

- 작성일: 2026-08-19
- 상태: Complete

## 목적

원본 Session과 Message를 수정하지 않고 ChatGPT 대화를 공통 `Task`와 `Activity` 모델로 읽기 전용 분석한다. 확실하지 않은 경계는 자동 분리하지 않고 candidate와 confidence로 유지한다.

## 구현

- 공통 `Task`, `Activity`, `MessageRange`, `Provenance` 모델 재사용
- 첫 실제 사용자 요청을 Task 시작점으로 사용
- 새 작업 표현, 단계 전환, 이전 완료 표현을 조합한 결정적 경계 점수 계산
- confidence 0.75 이상만 Task 경계로 제안
- confidence 0.4 이상 0.75 미만은 `boundary_candidates`에 기록하고 분리하지 않음
- Message role과 완료·실패·결정 표현으로 request, response, decision, note, result Activity 생성
- 최신 assistant 결과를 기준으로 in_progress, completed, failed 상태 결정
- Task/Activity provenance를 `source=derived`, `derived_by=rule`로 분리
- 원본 Session/Message provenance는 `source=original`로 유지
- ChatGPT Adapter 1.1 projection에 Task, Activity, candidate, analysis warning 추가
- 1.0 projection은 파일을 변경하지 않고 조회 시 동일 분석기를 적용
- Task 목록 및 상세 Activity 조회 API 추가

## API

- `GET /api/v1/chatgpt/tasks`
- `GET /api/v1/chatgpt/tasks?sessionId={session_id}`
- `GET /api/v1/chatgpt/tasks/{task_id}`

## 호환성

새 projection 필드는 기본 빈 tuple이므로 기존 immutable revision JSON을 계속 읽는다. 기존 ChatGPT 파싱 warning과 Task 분석 warning은 서로 다른 필드로 유지한다. Markdown, ChatGPT Clip 및 원본 archive 형식은 변경하지 않는다.

