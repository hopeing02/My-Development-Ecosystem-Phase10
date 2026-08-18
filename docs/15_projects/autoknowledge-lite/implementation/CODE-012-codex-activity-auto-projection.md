# CODE-012 Codex Activity 자동 투영

## 목표

공식 Codex `thread/read` 응답의 공개 이벤트를 기존 Windows Collector 자료와 통합하여 Knowledge Viewer의 명령, 변경 파일, Diff, 테스트 탭에 자동 표시한다.

## 구현

- `commandExecution`을 독립 `Command`로 승격한다.
- pytest, lint, build 등 기존 명령 분류기를 재사용하여 `Test`를 생성한다.
- 동일 명령이 `mde codex run`으로도 수집된 경우 하나의 명령에 `mde_wrapper`, `codex_session` 출처를 병합한다.
- `fileChange`의 안전한 경로, 변경 종류, 공개 Diff를 보존한다.
- Git snapshot과 동일 경로는 하나의 `changedFiles` 항목으로 병합한다.
- Codex 공개 Diff는 `captureMethod=codex_session` 첨부로 저장한다.
- 메시지가 추가되지 않았더라도 Activity 투영 결과가 달라지면 기존 capture ID의 새 revision을 전송한다.
- 재동기화 시 이전 Codex 파생 자료를 제거하고 현재 공개 이벤트에서 다시 계산하여 stale 자료를 남기지 않는다.

## 보안과 호환성

- `.env`, 키 파일 등 기존 민감 경로 규칙에 해당하는 변경은 경로와 Diff 모두 투영하지 않는다.
- 원본 공개 메시지 순서와 content hash 계약은 유지한다.
- 기존 wrapper 명령, Git snapshot, Markdown, queue, quarantine 경로는 변경하지 않는다.
- 이전 session-state에 신규 필드가 없어도 빈 배열로 처리한다.

## 사용자 동작

전체 대화 세션을 한 번 연결한 뒤 `mde codex sessions sync` 또는 finalize를 실행하면 공개 명령·파일 변경·Diff·테스트가 자동 투영된다. `mde codex run`은 계속 지원되며 더 정확한 stdout/stderr 파일과 실행 환경을 수집할 때 사용할 수 있다.
