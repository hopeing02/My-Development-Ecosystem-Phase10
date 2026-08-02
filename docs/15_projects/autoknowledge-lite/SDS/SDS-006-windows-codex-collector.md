# SDS-006 Windows Codex 작업 수집기

- 버전: 1.0
- 상태: Implemented

## 구성

```text
mde codex CLI
  -> project registry
  -> session state store
  -> Git snapshot and attribution
  -> command/output capture
  -> redaction and path aliases
  -> local artifacts
  -> POST /api/v1/captures
     -> DevelopmentSessionHandler
```

로컬 루트는 `%LOCALAPPDATA%\AutoKnowledgeLite\CodexCollector`이며 테스트에서는 `MDE_CODEX_HOME`으로 대체할 수 있다.

세션 상태는 `CREATED`, `CAPTURING`, `PAUSED`, `FINALIZING`, `SAVED`, `QUEUED`, `FAILED`, `ABANDONED`, `QUARANTINED`를 사용한다. 전송 실패 자료는 삭제하지 않는다.

출력은 stdout/stderr 각각 최대 1MB를 기준으로 앞뒤 256KB와 전체 해시를 저장한다. `.env`, 키, 인증서 및 저장소 내부의 민감 경로는 patch에서 제외한다.
