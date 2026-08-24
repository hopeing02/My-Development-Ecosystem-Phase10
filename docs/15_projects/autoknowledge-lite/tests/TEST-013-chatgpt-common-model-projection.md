# TEST-013 ChatGPT 공통 모델 Projection 검증

## 검증 범위

- 정상 ChatGPT export의 Session/Message 투영
- 기존 ChatGPT Clip Capture Envelope 호환
- 원본 Message ID와 정규화 SHA-256 기반 중복 제거
- 손상된 Message의 warning 격리와 유효 Message 보존
- 입력 export dict와 Clip payload 불변
- 필수 원본 Session 정보 누락 시 임의 생성 금지
- 기존 Codex Adapter와 Capture 저장 회귀
- AutoKnowledge-Lite 전체 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_knowledge_adapter.py tests/test_codex_knowledge_adapter.py tests/test_capture_api.py -q
# 29 passed, 1 skipped

uv run pytest -q
# 136 passed, 1 skipped

uv run ruff check .
# passed

uv run black --check src/autoknowledge_lite/chatgpt_knowledge_adapter.py tests/test_chatgpt_knowledge_adapter.py
# passed
```

## 기존 경고

전체 `uv run black --check .`는 이번 변경과 무관한 기존 파일 3개의 포맷 차이로
실패한다.

- `src/autoknowledge_lite/mde_client.py`
- `tests/test_mde_client.py`
- `tests/test_codex_control_api.py`

기존 Starlette deprecation warning과 pytest cache 권한 warning도 유지된다.
