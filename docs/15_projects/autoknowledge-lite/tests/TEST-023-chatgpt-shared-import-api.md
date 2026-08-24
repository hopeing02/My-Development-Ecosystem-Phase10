# TEST-023 ChatGPT Shared Link Import API 검증

## 검증 범위

- Control API Key 미설정 시 비활성화
- 명시적 link Import와 raw snapshot 생성
- response raw path, 원문과 Shared URL 비노출
- 손상 snapshot Archive 후 partial warning
- lookalike host URL 거부와 URL 비반사
- upstream fetch 실패의 안전한 502 응답
- `create_app` route 설치
- 기존 Export Import API 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_shared_import_api.py tests/test_chatgpt_import_api.py -q
# 12 passed

uv run ruff check src/autoknowledge_lite/chatgpt_import_api.py src/autoknowledge_lite/chatgpt_shared_import_api.py src/autoknowledge_lite/api.py tests/test_chatgpt_shared_import_api.py
# passed

uv run black --check src/autoknowledge_lite/chatgpt_import_api.py src/autoknowledge_lite/chatgpt_shared_import_api.py src/autoknowledge_lite/api.py tests/test_chatgpt_shared_import_api.py
# passed
```
