# TEST-012 Codex Activity 자동 투영 검증

## 검증 범위

- wrapper 없이 `commandExecution`에서 Command 생성
- pytest 명령과 출력에서 Test 및 passed 개수 생성
- `fileChange`에서 변경 파일과 Diff 생성
- wrapper와 Codex 양쪽에서 수집된 동일 명령 중복 제거
- Git snapshot 변경 파일과 Codex 변경 파일 병합
- 메시지가 동일한 기존 세션의 파생 Activity 재투영 및 revision 전송
- 민감 경로의 파일 변경과 Diff 제외
- 기존 Viewer populated/empty state 및 Task 양방향 링크 회귀

## 실행 명령과 결과

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10\packages\mde-core
uv run pytest tests/codex_capture -q
# 29 passed

Set-Location C:\My-Development-Ecosystem-Phase10\apps\autoknowledge-lite
uv run pytest tests/test_capture_api.py tests/test_capture_query.py tests/test_codex_knowledge_adapter.py -q
# 28 passed, 1 skipped

Set-Location C:\My-Development-Ecosystem-Phase10\apps\knowledge-viewer
npm test -- --run
# 28 passed

npm run build
# build succeeded
```

pytest cache 디렉터리 권한 및 기존 Starlette deprecation 경고가 있으나 테스트 실패는 아니다. Viewer production build의 기존 대형 chunk 경고도 유지된다.
