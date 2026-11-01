# STEP G2 — 배치 의존성 및 동일 브랜치 누적 실행

- 날짜: 2026-11-01 (Asia/Seoul)
- 기준: origin/main cc28ff0, G1 397206e 포함
- 지침: AGENTS.md, DEV-001, docs/development-guidelines
- 범위: G2. GitHub Actions, PR 자동 병합, Gate 확장, 실패 자동 복구는 후속 단계.

## 변경

수정: packages/mde-core/src/mde/sync/engine.py
신규: packages/mde-core/tests/sync/test_multi_step_batch.py

기존에는 STEP별 브랜치 분기로 결과 누적이 보장되지 않았다. 이제 metadata.batch_id와 depends_on을 지정한 작업은 같은 전용 브랜치에서 파일명 순으로 처리한다. 선행 작업 완료 상태와 STEP별 커밋이 확보되어야 후속 작업을 실행한다. 같은 배치 브랜치에서 정의가 동일한 완료 작업은 재실행하지 않는다.

재사용: TaskStore, load_task, execute_task, create_task_branch, checkout_branch, 기존 Git 함수. TaskStore/TaskDefinition/Agent/CheckpointStore는 변경하지 않았다.
신규 운영 함수: _validate_batch_plan. 기존 함수만으로 작업 간 의존성과 공유 브랜치 계약을 검사할 수 없어 추가했다.
수정 함수: run_mobile_sync 및 _commit_task_if_needed의 타입 표시.
신규 테스트 함수·도우미: 배치 실제 Git 커밋/상태 전이와 오류 중단을 검증하기 위해 추가했다. 별도 저장소나 오케스트레이션 계층은 만들지 않았다.

## 첨부 코드에서 보완한 사항

- run_tasks=False에서 dependencies 미초기화로 발생하는 UnboundLocalError를 수정했다. 기존 테스트 3개에서 실제 재현했다.
- 서로 다른 배치가 동일 브랜치를 공유하는 설정을 거부한다.
- 원래 실행 브랜치 또는 base_branch를 배치 전용 브랜치로 사용하는 설정을 거부한다.
- 브랜치 전환 후 작업 정의가 최초 계획과 다르면 중단한다.
- 실행기가 completed를 반환해도 TaskStore에 completed가 저장되지 않았으면 중단한다.
- 커밋 실패 또는 체크포인트 커밋 누락 시 다음 STEP을 시작하지 않는다.

## 실행

Python 3.12, 저장소 루트에서:

```powershell
uv sync --frozen --python 3.12
uv run pytest packages/mde-core/tests/sync/test_multi_step_batch.py -q
uv run pytest packages/mde-core/tests/sync/test_multi_step_baseline.py -q
uv run pytest -q
uv run ruff check .
uv run black --check .
```

실제 작업은 pending YAML을 Git에 등록한 뒤 아래 명령으로 실행한다.

```powershell
uv run mde agent --once --auto-save --no-push
```

현재 run_once는 --no-push만 지정하면 커밋도 끄므로 --auto-save가 필요하다. 작업 YAML에도 auto_apply/run_tests/auto_save: true, auto_push: false를 명시한다. 배치의 모든 STEP은 동일한 batch_id, repository.branch, base_branch를 사용하고 depends_on에는 파일명 순서상 앞선 같은 배치의 작업 ID만 지정한다.

```yaml
version: 1
task:
  id: STEP-002
  type: feature
  title: Second step
  workflow: feature
  repository:
    branch: feature/mde-g2-demo
    base_branch: main
  execution:
    auto_apply: true
    run_tests: true
    auto_save: true
    auto_push: false
  metadata:
    batch_id: MDE-G2-DEMO
    depends_on: [STEP-001]
```

STEP-001은 같은 설정으로 depends_on을 생략하고 01-STEP-001.yaml, 위 STEP은 02-STEP-002.yaml로 등록한다. AI 설정과 실제 개발 내용은 프로젝트별로 별도 지정한다.

## 운영 제한

자동 위상정렬은 하지 않는다. 독립 작업과 배치를 한 사이클에 혼합하지 않는다. pending에 없는 선행 작업도 거부한다. 완료 배치 재조회는 원래 main에서 실행하며 배치 브랜치의 기록으로 중복을 차단한다. 실패 배치의 재개는 G4 범위다.

실패 작업 트리와 브랜치는 조사할 수 있도록 남긴다. reset/clean/자동 병합은 하지 않는다. 성공 시 결과는 배치 브랜치에 보존되고 원래 브랜치로 복귀한다. 원래 브랜치에는 pending 파일이 병합 전까지 남을 수 있다. 실 Codex나 원격 쓰기는 테스트에서 실행하지 않는다.

이 테스트의 작업 실행기는 대역이다. 실제 Git 저장소, 브랜치, 커밋, 상태 YAML을 사용하지만 실제 AI 개발과 검증 Gate의 적정성까지 증명하지는 않는다.

## Git 저장 명령

```powershell
git add packages/mde-core/src/mde/sync/engine.py packages/mde-core/tests/sync/test_multi_step_batch.py docs/04_development/DEV-G2-multi-step-batch.md
git commit -m "feat(mde): add dependency-aware shared-branch step batch"
```

다음 STEP: G3 검증 Gate.

## 검증 기록

- Python 3.12.14, uv frozen lock 설치 후 실제 저장소에서 실행.
- 최종 G2 26개 + G1 2개: 28 passed (16.41초).
- Ruff: All checks passed.
- Black: 249 files would be left unchanged.
- git diff --check: 통과.
- 실 Git 브랜치에서 3 STEP 누적, STEP별 커밋, main 복귀, main 깨끗한 상태, 재조회 중복 실행 방지를 확인했다.
- 누락/자기/순환/역순 의존성, 중복 ID/의존성, 잘못된 metadata, 혼합 배치, 저장 정책 누락, 커밋 실패/누락, completed 상태 누락 및 작업 정의 변경을 검증했다.
- 기존 작업 폴더의 사용자 AGENTS.md 수정은 보존했고 별도 work/MDE-G2 작업 트리에서 개발했다.
- 상태: 로컬 개발 및 검증. 이번 G2 변경의 커밋/Push는 수행하지 않았다.
- 최종 전체 회귀: 348 passed, 1 skipped (64.34초).
