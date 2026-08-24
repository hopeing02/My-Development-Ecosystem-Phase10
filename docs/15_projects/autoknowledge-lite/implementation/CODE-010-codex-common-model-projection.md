# CODE-010 Codex 공통 모델 Projection

- 작성일: 2026-08-18
- 상태: Complete

## 구현

기존 `codex/development_session` Capture Envelope를 공통 `Session`과 `Message`로
변환하는 읽기 전용 `CodexKnowledgeAdapter`를 추가했다.

- 기존 `captureSessionId`, `sourceSessionId`, `messageId`, sequence와 content hash 재사용
- `captureSessionId`가 없을 때 이미 존재하는 `captureId` 사용
- `system_summary`를 공통 `system` role로 투영
- 원문 Message content를 정규화하거나 수정하지 않음
- 원본 provenance와 Capture·Message reference 기록
- ID, sequence, role 또는 content를 안전하게 변환할 수 없는 메시지는 임의 보강하지 않음
- 변환하지 못한 메시지는 원본에 그대로 남기고 projection warning 기록
- 원본 Capture payload, Session Markdown, 저장소와 Graph는 변경하지 않음

## 실패 경계

지원하지 않는 Source 또는 Capture 유형은 명시적 오류 코드로 거부한다. 개별
Message의 선택적 timestamp 또는 content hash가 유효하지 않으면 해당 선택 필드를
projection에서 제외하고 warning을 남긴다. 이 동작은 원본 Capture 저장 성공 여부에
영향을 주지 않는다.
