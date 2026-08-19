# TEST-029 Session Task 분석기 검증

- 실행일: 2026-08-19
- 상태: Passed

## 집중 테스트

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite
uv run pytest -q tests/test_task_analyzer.py `
  tests/test_chatgpt_knowledge_adapter.py `
  tests/test_chatgpt_import.py `
  tests/test_chatgpt_query_api.py
# 24 passed
```

검증 항목:

- 확실한 Task 경계 분리
- 불확실한 경계를 candidate로 유지
- request, response, decision, note, result Activity 생성
- 실패 후 성공한 최신 결과를 completed로 판정
- session mismatch와 duplicate sequence warning 격리
- 사용자 요청이 없는 대화에서 Task를 임의 생성하지 않음
- 원본 객체와 기존 projection revision 불변
- 기존 1.0 projection 조회 호환
- Task 목록·상세·Activity API
- 기존 ChatGPT warning 계약 유지

## 전체 회귀

```powershell
$env:AUTOKNOWLEDGE_CONTROL_API_KEY=''
uv run pytest -q
# 213 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check <Step 6 변경 Python 파일>
# 8 files unchanged
```

## 운영 경로

기존 ChatGPT 1.0 projection을 수정하거나 재가져오지 않은 상태에서 8765 gateway로 확인했다.

- 기존 Session: 1개
- 파생 Task: 1개
- Task Activity: 8개
- Task provenance: `derived`
