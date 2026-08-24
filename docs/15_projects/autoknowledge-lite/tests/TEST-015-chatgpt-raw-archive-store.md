# TEST-015 ChatGPT Raw Archive Store 검증

## 검증 범위

- 원본 ZIP과 동일한 local raw Archive 저장
- source ZIP 불변
- manifest 필드와 원본 member 기록
- 보관된 ZIP을 Session Source로 다시 읽기
- 동일 Archive Import 멱등성과 중복 디렉터리 방지
- discovery warning code 기록
- discovery 이후 source 변경 감지
- 손상된 기존 manifest 보호
- timezone 없는 clock 거부와 부분 데이터 미생성
- AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_archive.py -q
# 6 passed

uv run pytest -q
# 151 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/chatgpt_archive.py tests/test_chatgpt_archive.py
# passed
```

기존 Starlette deprecation warning과 pytest cache 권한 warning은 유지된다.
