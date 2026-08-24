# TEST-017 ChatGPT Export Import CLI 검증

## 검증 범위

- 정상 Export Import와 projection 생성
- 부분 손상 Session warning과 raw Archive 보존
- 동일 Archive 중복 Import 상태
- 존재하지 않는 ZIP의 구조화된 오류와 종료 코드
- CLI 출력의 raw Archive 경로 비노출
- 기존 CLI를 포함한 AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_cli.py -q
# 4 passed

uv run pytest -q
# 160 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/cli.py tests/test_chatgpt_cli.py
# passed
```

기존 Starlette deprecation warning과 pytest cache 권한 warning은 유지된다.
