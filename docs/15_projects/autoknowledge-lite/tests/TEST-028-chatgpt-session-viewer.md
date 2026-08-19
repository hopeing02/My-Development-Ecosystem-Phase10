# TEST-028 ChatGPT 실제 세션 Viewer 통합 검증

- 실행일: 2026-08-19
- 상태: Passed

## AutoKnowledge-Lite

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite
$env:AUTOKNOWLEDGE_CONTROL_API_KEY=''
uv run pytest -q
# 204 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/api.py `
  src/autoknowledge_lite/chatgpt_import.py `
  src/autoknowledge_lite/chatgpt_query.py `
  tests/test_chatgpt_query_api.py
# 4 files unchanged
```

전체 Black 검사는 이번 변경과 무관한 기존 파일 3개의 포맷 차이를 보고했다. 이번 변경 파일은 모두 통과했다.

## MDE Knowledge

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10
uv run pytest -q packages/mde-core/tests/knowledge
# 68 passed

uv run ruff check packages/mde-core/src/mde/knowledge packages/mde-core/tests/knowledge
# passed
```

## Knowledge Viewer

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\knowledge-viewer
npm test -- --run
# 10 test files, 37 tests passed

npm run build
# passed
```

## 운영 경로

- `GET /api/v1/chatgpt/sessions`: Session 1개
- Session detail: Message count 9개
- Message API: 9개 반환
- Graph API: Session 1개, Message 9개, edge 9개
- `http://100.75.235.67:8765/`: HTTP 200
