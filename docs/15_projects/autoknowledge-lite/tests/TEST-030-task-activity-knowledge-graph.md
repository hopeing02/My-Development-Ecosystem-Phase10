# TEST-030 Task/Activity Knowledge Graph 통합 검증

- 실행일: 2026-08-19
- 상태: Passed

## 집중 검증

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite
uv run pytest -q tests/test_chatgpt_query_api.py tests/test_capture_query.py
# 14 passed
```

검증 항목:

- ChatGPT graph의 Session, Message, Task, Activity 노드
- contains_message, contains_task, contains_activity, derived_from 관계
- graph metadata에 원본 Message content가 포함되지 않음
- 기존 `/api/v1/graph` 병합
- ChatGPT Task 중심 neighborhood 조회
- sourceType 필터 격리
- dangling edge 제거 및 기존 Capture graph 회귀

## 전체 회귀

```powershell
# AutoKnowledge-Lite
uv run pytest -q
# 214 passed, 1 skipped
uv run ruff check .
# passed

# Knowledge Viewer
npm test -- --run
# 10 test files, 38 tests passed
npm run build
# passed

# MDE Knowledge
uv run pytest -q packages/mde-core/tests/knowledge
# 68 passed
```

## 운영 경로

8765의 통합 `/api/v1/graph`를 실제 보존 Session에 대해 확인했다.

- ChatGPT Session node: 1개
- ChatGPT Message node: 9개
- Task node: 1개
- Activity node: 8개
- 관련 edge: 26개
- graph warning: 0개
- Tailscale Viewer: HTTP 200

