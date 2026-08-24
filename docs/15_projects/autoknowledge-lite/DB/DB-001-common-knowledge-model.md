# DB-001 AutoKnowledge 공통 지식 모델

- 버전: 1.0
- 상태: Implemented
- 작성일: 2026-08-18

## 목적

기존 Markdown, Capture Envelope v1과 Codex 수집 자료를 변경하지 않고 그 위에
`Session → Task → Activity` 구조를 표현할 공통 내부 계약을 정의한다. 이 단계는
저장소, Knowledge Graph, Viewer와 연결하지 않는다.

## 객체

- `Session`: ChatGPT, Codex 또는 기타 원본 세션
- `Message`: 원문을 변경하지 않는 세션 메시지
- `Task`: 메시지 범위로 표현되는 작업 단위
- `Activity`: request, response, decision, command, file change, test, result, note
- `Decision`: 결정 요약과 근거
- `FileRecord`: Task에 귀속된 파일 변경
- `CommandRecord`: 명령, 실행 시각, 출력과 exit code
- `TestRecord`: 테스트 명령, 상태와 결과
- `ResultRecord`: Task 결과와 변경 파일·테스트 참조

## 원본과 파생 자료

모든 객체는 `Provenance`를 가진다.

- `source=original`: 원본 Capture 또는 Adapter에서 확인된 자료
- `source=derived`: AI, 규칙 또는 사용자 작업으로 생성된 자료
- 파생 자료는 `derived_by`를 필수로 기록한다.
- confidence는 0 이상 1 이하이며 파생 자료에만 기록한다.
- `source_refs`는 원본 Message, Capture 또는 다른 근거 ID를 참조한다.

원본 Message의 content는 정규화하거나 재작성하지 않는다.

## 무결성

- 모든 시각은 timezone을 포함한다.
- Task의 message range와 시작·완료 시각은 역전될 수 없다.
- renamed 파일에는 이전 경로가 필요하다.
- 모델은 알 수 없는 필드를 거부하고 생성 후 변경할 수 없다.
- 기존 Capture Envelope v1, Markdown 포맷과 저장 위치는 변경하지 않는다.

## 후속 연결

다음 단계에서 기존 Codex `development_session` payload를 이 모델로 투영한다.
투영 또는 Task 분석 실패는 원본 Capture와 Session Markdown 저장 성공에 영향을
주지 않아야 한다.
