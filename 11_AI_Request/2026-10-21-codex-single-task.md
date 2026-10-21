# MDE-CODEX-W1

- 요청 ID: MDE-CODEX-W1
- 작성일: 2026-10-21
- 대상 AI: Codex
- 목적: DevelopmentTask JSON 한 건을 기존 Codex CLI와 독립 tools/automation 실행기로 처리한다.
- 요청 내용: 기존 라이브러리·검증 코드를 찾아 재사용하고 운영 코드·테스트·예제·STEP MD를 구현한다.
- 제약 조건: 기존 Codex Provider/Workflow/task_runner 재작성 없음. mde save, commit/push, 배포, 반복 수정, 멀티에이전트 연결 없음.
- 기대 결과: 실제 CLI 한 건, 허용 경로 검사, pytest/Ruff/Black, PASS/FAIL result.json, 기존 회귀 검사 기록.
- 처리 상태: W1 구현·실 CLI 1건·회귀 검증 PASS. CODE-015 / TEST-021 참조. 검토 후 사용자 별도 요청으로 W1 소스 commit/push 진행.
