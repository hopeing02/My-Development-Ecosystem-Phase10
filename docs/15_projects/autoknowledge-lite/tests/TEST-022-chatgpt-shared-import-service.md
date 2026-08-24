# TEST-022 ChatGPT Shared Link Import Service 검증

## 검증 범위

- raw snapshot 보존 후 original Session/Message 투영
- 동일 raw와 projection 중복 방지
- 같은 conversation의 갱신 snapshot revision 증가
- 손상 snapshot의 raw 보존과 warning 격리
- title 등 필수 원본 필드 누락 시 데이터 미생성
- 기존 Export Import content hash 전략 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_shared_import.py tests/test_chatgpt_import.py -q
# 10 passed

uv run ruff check src/autoknowledge_lite/chatgpt_import.py src/autoknowledge_lite/chatgpt_shared_import.py tests/test_chatgpt_shared_import.py
# passed

uv run black --check src/autoknowledge_lite/chatgpt_import.py src/autoknowledge_lite/chatgpt_shared_import.py tests/test_chatgpt_shared_import.py
# passed
```
