# TEST-021 ChatGPT Shared Snapshot Fetch와 Archive 검증

## 검증 범위

- 명시적 canonical URL의 HTML streaming fetch
- request에 cookie와 Authorization 미포함
- 다른 conversation과 외부 URL redirect 거부
- content type과 선언/실제 byte 크기 제한
- raw snapshot atomic 저장과 content hash 중복 방지
- manifest에 raw share ID 비노출
- 손상된 기존 Archive와 변경된 content hash 거부

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest tests/test_chatgpt_shared_archive.py -q
# 8 passed

uv run ruff check src/autoknowledge_lite/chatgpt_shared_archive.py tests/test_chatgpt_shared_archive.py
# passed

uv run black --check src/autoknowledge_lite/chatgpt_shared_archive.py tests/test_chatgpt_shared_archive.py
# passed
```
