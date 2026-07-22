# TEST-006 MDE 문서 동기화 검증

- 상태: Passed
- 작성일: 2026-07-22

## 대상

- `mde docs check`
- `mde docs update`
- `mde docs update --apply`
- CLI parser 기반 참조 생성
- 관리 구간 보호

## 사전 조건

- Python 3.11 이상
- uv 사용 가능
- MDE 저장소 루트 또는 하위 경로
- `CMD-004-mde-user-guide.md`에 정확한 관리 표식 한 쌍 존재

## 절차

```powershell
uv run pytest -p no:cacheprovider packages/mde-core/tests/docs/test_sync.py tests/test_mde_cli.py -q
uv run pytest -p no:cacheprovider -q
uv run ruff check . --exclude .runtime,.test-deps,.incoming,.codex-remote-attachments,apps/autoknowledge-lite/android,apps/autoknowledge-lite/data,apps/autoknowledge-lite/vault,apps/autoknowledge-lite/src/autoknowledge_lite.egg-info
uv run ruff format --check packages/mde-core/src/mde/documentation.py packages/mde-core/src/mde/cli.py packages/mde-core/tests/docs/test_sync.py
uv run mde docs check
uv run mde docs update
uv run mde docs update --apply
uv run mde docs check
```

## 예상 결과

- 실제 CLI가 참조 구간에 반영된다.
- 미리보기는 파일을 수정하지 않는다.
- `--apply`는 관리 구간만 수정한다.
- 표식 오류는 안전하게 거부된다.
- 기존 MDE 기능에 회귀가 없다.

## 실제 결과

- 전용 및 CLI 테스트: 9 passed
- 전체 회귀 테스트: 142 passed
- Ruff: passed
- Formatter: passed
- 최초 check: out of date 탐지
- update: diff 출력, 무변경
- update --apply: 관리 구간 갱신
- 최종 check: up to date

결과: Passed
