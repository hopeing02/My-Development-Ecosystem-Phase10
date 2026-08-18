# TEST-016 ChatGPT Import Projection Revision 검증

## 검증 범위

- 정상 Session projection과 필수 정보 손상 Session 격리
- 원본 ZIP과 JSON 불변
- 부분 손상 Message warning과 유효 content 보존
- warning report 별도 저장
- 동일 Export 재Import 시 revision 중복 방지
- 동일 Session 변경 시 revision 증가와 이전 revision 보존
- 손상된 기존 revision 보호
- AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_import.py -q
# 5 passed

uv run pytest -q
# 156 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/chatgpt_import.py tests/test_chatgpt_import.py
# passed
```

기존 Starlette deprecation warning과 pytest cache 권한 warning은 유지된다.
