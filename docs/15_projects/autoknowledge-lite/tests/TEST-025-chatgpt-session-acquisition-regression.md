# TEST-025 ChatGPT 실제 Session 확보 최종 회귀

- 실행일: 2026-08-18
- 상태: Passed

## AutoKnowledge-Lite

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite

uv run pytest -q
# 197 passed, 1 skipped

uv run ruff check .
# passed
```

ChatGPT Export와 Shared Link 통합에서 추가·수정한 Python source/test 19개에 대한
`black --check`도 통과했다. 기존 Starlette deprecation warning과 pytest cache 권한
warning은 테스트 실패가 아니며 이번 변경에서 새로 발생한 회귀가 아니다.

## Knowledge Viewer

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\knowledge-viewer

npm test
# 10 files passed, 35 tests passed

npm run build
# TypeScript checks and Vite production build passed
```

기존 Vite 500 kB chunk size 권고는 유지된다.

## 회귀 확인

- 기존 Markdown과 Document navigation 유지
- 기존 ChatGPT/Codex Clip과 Capture navigation 유지
- 기존 Codex Session, Task, Activity Viewer 유지
- 기존 Export ZIP 원본 보존, 중복 방지와 projection 유지
- Shared Link 손상 시 raw 보존과 warning 격리
- Viewer에서 Documents, Capture, ChatGPT 화면 전환 유지
- Control API Key와 원문을 browser storage 또는 API response에 기록하지 않음
