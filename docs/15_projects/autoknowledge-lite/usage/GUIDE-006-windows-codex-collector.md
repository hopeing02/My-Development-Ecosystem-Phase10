# GUIDE-006 Windows Codex 작업 수집기

1. `mde codex doctor`로 Git, Codex 탐지, 저장 경로와 queue를 확인한다.
2. 저장소를 한 번 등록한다.
3. Codex 작업 전에 `mde codex start`를 실행한다.
4. 검증 명령은 `mde codex run -- COMMAND`로 실행한다.
5. `mde codex finalize --summary TEXT`로 작업을 종료한다.
6. 결과가 `QUEUED`이면 서버 복구 후 `mde codex retry`를 실행한다.

민감정보 거부 세션은 quarantine에 남으며 자동 retry되지 않는다. 세션 원본을 확인하고 안전한 새 세션으로 다시 수집해야 한다.
