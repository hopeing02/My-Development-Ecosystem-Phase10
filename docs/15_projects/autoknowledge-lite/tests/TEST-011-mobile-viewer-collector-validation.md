# TEST-011 모바일 Viewer Collector 검증

## 목적

Collector 세션을 통해 모바일 Viewer의 대화, 명령, 변경 파일, Diff, 테스트 탭이 모두 채워지는지 검증한다.

## 검증 세션

- Capture session: `cap_codex_20260818_102231_2f9920e3`
- 실행 명령: `git status --short`
- 테스트: `uv run pytest apps/autoknowledge-lite/tests/test_capture_query.py`
- 완료 조건: 최종 Collector 상태가 `SAVED`이다.
