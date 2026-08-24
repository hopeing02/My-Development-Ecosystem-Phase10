# TEST-018 ChatGPT Export Import API 검증

## 검증 범위

- control key 미설정 시 endpoint 비활성화
- Bearer token 누락과 불일치 거부
- ZIP streaming Import와 projection 생성
- 응답 raw Archive 경로 비노출
- 성공 후 staging 정리
- 지원하지 않는 content type 사전 거부
- 잘못된 ZIP 오류와 staging 정리
- 설정된 upload 크기 제한과 staging 미생성
- 기존 API를 포함한 AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_import_api.py -q
# 6 passed

uv run pytest -q
# 166 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/chatgpt_import_api.py src/autoknowledge_lite/api.py tests/test_chatgpt_import_api.py
# passed
```

기존 Starlette deprecation warning과 pytest cache 권한 warning은 유지된다.
