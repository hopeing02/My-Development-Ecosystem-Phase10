# TEST-008 Windows Codex 작업 수집기

## 자동 검증

- 프로젝트 등록과 Git 저장소 검증
- 시작 전 dirty 변경 보존
- 세션 중 생성 및 추가 수정 귀속
- 경로 별칭과 민감정보 마스킹
- 명령 성공, 실패, timeout, stdout/stderr 저장
- session JSON, Markdown, patch 생성
- 서버 장애 queue
- Capture API 저장, 멱등 재전송, revision 증가
- `mde save` 실패 독립성

## 명령

```powershell
uv run pytest packages/mde-core/tests/codex_capture/test_collector.py -q
$env:PYTHONPATH='apps/autoknowledge-lite/src'
uv run pytest apps/autoknowledge-lite/tests/test_capture_api.py -q
uv run ruff check packages/mde-core/src/mde/codex_capture packages/mde-core/src/mde/cli.py apps/autoknowledge-lite/src/autoknowledge_lite/capture_api.py
```
