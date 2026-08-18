# TEST-014 ChatGPT Export Session Source 검증

## 검증 범위

- 정상 Export ZIP의 Session 발견과 개별 Session 읽기
- 원본 ZIP 불변 및 파일 미추출
- 분할 conversations JSON 지원
- Session ID 중복 제거
- 손상 JSON, 비객체 record와 ID 누락 warning 격리
- ZIP 경로 순회 차단
- 전체 압축 해제 크기 제한
- 중복 member 경로 차단
- conversations JSON 누락, 파일 누락과 잘못된 ZIP 오류
- AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_session_source.py -q
# 9 passed

uv run pytest -q
# 145 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/chatgpt_session_source.py tests/test_chatgpt_session_source.py
# passed
```

기존 Starlette deprecation warning과 pytest cache 권한 warning은 유지된다.
