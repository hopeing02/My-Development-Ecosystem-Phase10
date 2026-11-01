# CODE-018 MDE-D3 — TaskStore 실행이력과 실제 개발일지 연결

- 일자: 2026-11-01 (Asia/Seoul)
- 기준: codex/mde-d1-daily-plan / 1dd8142
- 입력: MDE_STEP_D3_Phase10_Files.zip
- 검증 기록: [TEST-024](../12_test/TEST-024-mde-daily-task-link.md)

## 목표와 범위

이미 기록된 D2 실적 한 건을 사용자가 선택한 종료된 YAML Task 실행 결과와 연결한다.
작업 자체를 실행하거나 D2의 검증 상태를 변경하지 않는다.
기존 개발 순서는 D1 계획 → D2 실제 개발일지 → D3 결과 연결 → D4 미완료 이월이다.

운영 파일은 tools/mde_daily_task_link.py, 테스트는 tools/tests/test_mde_daily_task_link.py다.
기존 D1·D2, 보류 mde_daily_result.py, TaskStore, Workflow, 앱, 의존성은 변경하지 않는다.
새 DB·API·공통 Framework·Task 실행·자동 Git 기능은 만들지 않는다.

## 기존 재사용과 신규 함수 필요성

- mde_daily_plan.validate_day, daily_log_path, list_app_projects, STEP_PATTERN.
- mde_daily_log.RECORD_PREFIX, HEADINGS, HEADING_PATTERN.
- 실제 mde.task.store.TaskStore.find, TaskDirectories 및 mde.task.loader.load_task.
- 신규 운영 함수: link_task_result, main 두 개만 추가한다.
- 신규 이유: D2 실제 실적 기준의 안전한 결과 연결과 독립 CLI 진입점이 필요하다.
- 기존 수정 함수: 없음.

보류된 이전 결과 연결 코드는 D1 계획을 전제로 하므로 D2 실제 기록 연결에 그대로 호출할 수 없다.
이 코드를 바꾸거나 실행 큐와 연결하지 않고 D3의 입력 계약만 추가한다.

TaskStore.__init__는 조회에서도 누락된 상태 디렉터리를 생성한다. D3는 이 생성자를 호출하지 않고
실제 TaskStore 인스턴스의 조회용 필드(repository_root, root, dirs)를 현재 저장소에 연결해
기존 find를 사용한다. TaskDirectories는 기존 클래스다. 별도 검색기·저장소·테스트용 가짜 모듈을 만들지 않는다.
현재 find가 사용하는 기존 상태 계약을 테스트하고, 상태 디렉터리가 없어도 미리보기가 생성하지 않음을 확인한다.

## 입력과 저장 계약

프로젝트는 실제 앱 또는 저장소 내부 packages/mde-core가 있는 mde-core다.
날짜 일지에는 표준 5개 제목이 순서대로 있고, 오늘 작업에 해당 프로젝트·STEP의
D2 실적이 정확히 한 건 있어야 한다. 보완 기록을 원본 실적의 중복으로 세지 않는다.

Task는 실제 tasks/completed 또는 tasks/failed의 YAML이어야 한다.
TaskStore의 별도 파일명 조회도 지원하며 YAML 내부 ID, 결과 ID·Workflow·상태를 대조한다.
project/project_id, step/step_id가 있으면 각각 모두 일치해야 한다.
두 종류의 메타데이터가 모두 확인되면 메타데이터 일치, 누락되면 사용자 지정 연결로 표시한다.
서로 충돌하는 별칭이나 잘못된 값은 거부한다.

결과는 UTF-8 YAML, 최대 1,000,000바이트이고 유효한 단계 목록이어야 한다.
test.run은 실패 → 생략 → 단계 완료 → 기록 없음 순서로 보수적으로 표시한다.
단계 완료는 실제 테스트 통과를 의미하지 않으며 D2 검증완료를 자동 선언하지 않는다.
Task/결과의 원시 오류·로그·제목·코드·민감 본문을 일지에 복제하지 않는다.

미리보기는 파일·작업 상태·디렉터리를 변경하지 않는다.
--write만 오늘 작업 제목 아래 D3 연동 한 줄을 삽입한다.
같은 날짜의 같은 Task ID는 다른 STEP을 선택해도 두 번째 연결을 거부한다.
다른 Task 두 개를 같은 D2 실적에 연결할 수 있다.
BOM·LF/CRLF·다른 기록을 보존하고 D1/D2와 동일한 날짜별 잠금을 사용한다.
원자 교체 직전 일지·Task·결과가 바뀌면 기록을 중단한다.

## 실행

저장소 루트에서 실행한다. TASK-ID-REAL은 예시이며 실제 종료된 YAML Task ID로 바꿔야 한다.
날짜·프로젝트·STEP도 해당 일지의 실제 D2 실적으로 지정한다.

```powershell
uv run --frozen python tools/mde_daily_log.py show --date 2026-10-31
uv run --frozen python tools/mde_daily_task_link.py --date 2026-10-31 --project mde-core --step MDE-D2 --task-id TASK-ID-REAL
uv run --frozen python tools/mde_daily_task_link.py --date 2026-10-31 --project mde-core --step MDE-D2 --task-id TASK-ID-REAL --write
uv run --frozen python tools/mde_daily_log.py show --date 2026-10-31
```

단독 스크립트 및 python -m tools.mde_daily_task_link를 지원한다.
성공 exit 0, 검증·파일 오류 exit 1, argparse 사용 오류 exit 2다.
pending/processing Task와 독립 W1 JSON 요청·결과는 연결 대상으로 사용하지 않는다.

## 실제 운영 상태

사용자가 이번 대화에서 운영 연동에 사용할 결과가 아직 없다고 확인했다.
현재 로컬 TaskStore에는 tasks/pending/DOC-PARSER-1.json만 있으며 종료된 YAML은 없다.
따라서 실제 성공 Task 연결 E2E를 완료로 표시하지 않는다.
검증을 위해 운영 저장소에 Task/결과를 만들거나 작업을 실행하지 않는다.
임시 저장소에서 실제 TaskStore.claim/complete/fail과 실제 로더를 사용해 기능을 검증한다.
이는 실제 사용자 실행 결과 연결과 구분한다. 운영 이력이 생기면 미리보기부터 확인한다.

## 검증과 Git 명령

```powershell
uv run --frozen pytest tools/tests/test_mde_daily_task_link.py tools/tests/test_mde_daily_plan.py tools/tests/test_mde_daily_log.py -q
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen black --check .
uv run --frozen mde docs check
uv run --frozen mde docs check --target knowledge-guide
git diff --check
```

코드·격리 통합 검증과 운영 결과 부재를 검토한 뒤 사용할 선택적 커밋 명령이다.
작업 전부터 있던 미커밋 2026-11-01.md 일지는 이 STEP 커밋 대상에 임의 포함하지 않는다.

```powershell
git add tools/mde_daily_task_link.py tools/tests/test_mde_daily_task_link.py docs/11_code/CODE-018-mde-daily-task-link.md docs/12_test/TEST-024-mde-daily-task-link.md 11_AI_Request/2026-11-01-codex-mde-d3.md
git commit -m "feat(mde): link TaskStore execution results to daily development log"
```

D3 실제 운영 결과 연결 확인 후에 D4 미완료 이월을 진행한다.
