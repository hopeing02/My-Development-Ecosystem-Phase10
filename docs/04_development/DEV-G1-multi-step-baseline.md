# STEP G1 — 다중 STEP 기준동작 검증

- 검증일: 2026-10-31 (Asia/Seoul)
- 기준 저장소: hopeing02/My-Development-Ecosystem-Phase10
- 기준 커밋: e6d389e65c8f27e343eb3096367c06b9291ba990
- 범위: 기존 sync 동작을 고정하는 테스트 추가. 운영 코드 변경 없음.

## 구현 및 판정

첨부 test_multi_step_baseline.py를 packages/mde-core/tests/sync/에 그대로 추가했다.
첫 테스트는 역순으로 생성한 pending 파일이 파일명 순서로 실행되고 모두 completed로 이동하는지 검사한다.
둘째 테스트는 STEP-002 실패 후 SyncError에 실패 ID가 포함되고 STEP-003이 pending에 남는지 검사한다.
실제 TaskStore와 상태 파일을 사용하며 Git 네트워크 호출과 작업 실행기는 대역으로 교체한다.

재사용 함수: run_mobile_sync, TaskStore.list/claim/complete/fail/find, utc_now.
신규 함수: 테스트 2개와 임시 YAML 작성 및 Git 대역 설정 도우미 2개.
수정 함수: 없음. 테스트 도우미는 독립적인 시험 데이터와 외부 Git 격리에 필요하다.

## 재현

Python 3.12 환경에서 저장소 루트 기준:

```powershell
uv sync --frozen --python 3.12
uv run pytest packages/mde-core/tests/sync/test_multi_step_baseline.py -q
uv run pytest packages/mde-core/tests/sync packages/mde-core/tests/task packages/mde-core/tests/agent -q
uv run pytest -q
uv run ruff check .
uv run black --check .
```

## 검증 범위와 다음 단계

정책은 auto_commit=False, auto_push=False, task_branches=False다.
이 테스트만으로 agent --once의 브랜치별 실제 코드 누적, 의존성 검사, Gate, 재개 또는 GitHub Actions 통합이 검증되지는 않는다.
다음 G2는 TaskStore를 재사용하면서 배치 코드 누적과 의존성 검사를 구현한다.
GitHub 원격 변경 및 실제 Codex 호출은 수행하지 않았다.

검토 후 저장할 명령:

```powershell
git add packages/mde-core/tests/sync/test_multi_step_baseline.py docs/04_development/DEV-G1-multi-step-baseline.md
git commit -m "test(mde): establish multi-step sync baseline"
```

## 실제 검증 결과

- 신규 기준동작 테스트: 2 passed.
- sync/task/agent 회귀: 24 passed.
- 전체 회귀: 322 passed, 1 skipped (51.02초).
- Ruff: All checks passed.
- Black: 248 files would be left unchanged.
- 운영 코드 변경: 0건.
- 상태: 구현 및 로컬 검증 완료, 변경 커밋 및 원격 반영 미수행.
- 기준 커밋은 위에 기록했으며 변경 커밋 해시는 아직 없다.
