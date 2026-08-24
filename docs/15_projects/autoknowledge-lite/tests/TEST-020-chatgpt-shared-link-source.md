# TEST-020 ChatGPT Shared Link Source 검증

## 검증 범위

- nested JSON string에 포함된 실제 conversation 탐색
- source snapshot 원본 불변
- canonical HTTPS ChatGPT Shared Link URL 제한
- lookalike host, credential, query, 잘못된 port 거부
- 반복 payload content hash 중복 제거
- 여러 conversation 중 URL ID 일치 후보 선택과 warning
- 손상 snapshot 오류 격리
- snapshot 크기 제한
- 기존 ChatGPT Adapter의 original Session/Message provenance
- 현재 `/share/` ChatGPT Clip 내용 추출 호환

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_shared_link_source.py tests/test_content.py tests/test_chatgpt_knowledge_adapter.py -q
# 21 passed

uv run ruff check src/autoknowledge_lite/chatgpt_shared_link_source.py src/autoknowledge_lite/content.py tests/test_chatgpt_shared_link_source.py tests/test_content.py
# passed

uv run black --check src/autoknowledge_lite/chatgpt_shared_link_source.py src/autoknowledge_lite/content.py tests/test_chatgpt_shared_link_source.py tests/test_content.py
# passed

uv run pytest -q
# 178 passed, 1 skipped
```
