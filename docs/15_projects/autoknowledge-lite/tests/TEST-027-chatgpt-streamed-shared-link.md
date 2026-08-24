# TEST-027 ChatGPT streamed Shared Link 회귀 검증

- 실행일: 2026-08-19
- 상태: Passed

## 집중 테스트

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest -q tests/test_chatgpt_shared_link_source.py `
  tests/test_chatgpt_shared_archive.py `
  tests/test_chatgpt_shared_import.py `
  tests/test_chatgpt_shared_import_api.py
# 34 passed
```

- 기존 중첩 JSON Shared Link 유지
- streamed loader reference table 복원
- reference table의 순환 관계 안전 종료
- 원본 snapshot byte 불변
- 손상 snapshot warning 격리 유지

## 전체 회귀

```powershell
$env:AUTOKNOWLEDGE_CONTROL_API_KEY=''
uv run pytest -q
# 200 passed, 1 skipped

uv run ruff check .
# passed
```

## 보존 원본 및 운영 재처리

- 보존 snapshot read-only 검증: Session 1, mapping node 19, Message 9
- provenance: `original`
- 운영 API 재처리: `status=imported`
- 발견 1, 신규 1, 중복 0, 실패 0
- warning 2건은 원본 mapping의 중복 content와 content 없는 node 격리 기록이며
  Session 저장 실패가 아니다.
