# TEST-007 AutoKnowledge Vault Source 연결 검증

- 상태: Passed
- 작성일: 2026-07-22

## 대상

- `autoknowledge-vault` Source 등록
- Category와 Agent 접근 기본값
- 최초 및 증분 스캔
- Source 제한 검색
- 민감 Source 기본 검색 제외
- 감사 로그 개인정보 보호

## 사전 조건

- MDE Knowledge Plugin v1.2.0
- 사용자 로컬 SQLite 3.42.0과 FTS5 지원
- 읽기 가능한 AutoKnowledge 개인 Vault

## 절차

```powershell
uv run mde knowledge add <vault-path> --name autoknowledge-vault --category personal --type obsidian
uv run mde knowledge show autoknowledge-vault
uv run mde knowledge scan autoknowledge-vault
uv run mde knowledge search "AutoKnowledge" --source autoknowledge-vault --limit 5
uv run mde knowledge scan autoknowledge-vault
uv run mde knowledge search <unique-query> --limit 5
uv run mde knowledge search <unique-query> --all --limit 5
```

## 예상 결과

- `personal`, `obsidian`, `sensitive=true`, `agent access=false`로 등록된다.
- Markdown 18개가 오류 없이 색인된다.
- 재스캔에서는 18개가 모두 `Unchanged`다.
- Source를 명시한 검색에서만 민감 결과가 표시된다.
- 기본 검색과 `--all`만 사용한 검색은 민감 결과를 반환하지 않는다.
- 감사 로그에 Source 절대경로가 기록되지 않는다.
- 원본 파일은 변경되지 않는다.

## 실제 결과

```text
Source ID: ks-002
Category: personal
Type: obsidian
Sensitive: true
Agent access: false
Documents: 18

First scan: Added 18, Errors 0
Incremental scan: Unchanged 18, Errors 0
Default search exposed sensitive source: false
--all exposed sensitive source: false
Audit log contains absolute vault path: false
```

결과: Passed
