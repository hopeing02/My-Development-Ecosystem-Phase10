# CODE-017 MDE-D2 — 실제 개발일지 입력·저장·조회·보완

- 일자: 2026-10-31 (Asia/Seoul)
- 기준 브랜치: codex/mde-d1-daily-plan / 865f608
- 입력: 사용자 개발 순서 정정 및 MDE_STEP_D2_Phase10_ActualLog.md
- 검증: [TEST-023](../12_test/TEST-023-mde-actual-daily-log.md)

## 목표와 개발 순서

일일 계획과 실제 실적을 구분해 기존 날짜별 개발일지에 실제 작업을 입력하고 조회한다.
현재 순서는 D1 계획(사용자 확인 완료) → D2 실제 개발일지 → D3 TaskStore 연동 → D4 미완료 이월이다.
기존 mde_daily_result.py 및 그 테스트는 삭제·수정하지 않고 D3 후보로 보류한다.
해당 코드의 과거 D2 명칭과 결과 접두사는 이전 구현의 기록이며 이번 D2의 사용 명령은 아니다.

## 기존 재사용과 신규 코드

D1의 list_app_projects, validate_day, daily_log_path, STEP_PATTERN을 실제 참조한다.
기존 logging.logger는 실행 로그이고, mde_toolkit.write_file은 템플릿 생성 계약으로
5개 항목별 실적 보존·중복 방지 기능을 제공하지 않는다. D1 등록 함수를 변경하지 않고 독립 도구를 추가한다.

- 신규 운영 함수: record_work, main.
- 필요성: 실적 검증·항목별 삽입·보완과 명시적인 CLI 진입점.
- 신규 운영 파일: tools/mde_daily_log.py.
- 신규 테스트 파일: tools/tests/test_mde_daily_log.py.
- 기존 수정 운영 함수: 없음.
- 신규 DB·API·AI·작업 큐·의존성: 없음.

앱은 D1의 실제 apps 목록을 사용하고 sample-project를 제외한다.
MDE 자체 공통 개발은 실제 packages/mde-core 디렉터리가 저장소 내부에 있을 때만
프로젝트 mde-core로 기록한다. D1 앱 선택 범위는 유지한다.

## 실행

저장소 루트에서 실행한다. 내용은 실제 수행 사실로 입력하고 시간은 측정한 경우에만 지정한다.
날짜 생략 시 실행 PC의 로컬 날짜를 사용한다.

```powershell
python tools/mde_daily_log.py record --date 2026-10-31 --project mde-core --step MDE-D2 --work "실제 개발일지 기능 구현" --result "저장·조회 확인" --next "사용자 실사용 확인"
python tools/mde_daily_log.py show --date 2026-10-31
```

소요시간 생략은 미계측이다. 측정한 실제 정수 1~720분은 --minutes로 입력한다.
검증 상태 기본값은 미검증이다. 검증완료/검증실패는 사람이 확인한 --evidence가 필요하며,
문자열 근거가 사실인지 자동 판단하거나 사용자 확인을 만들어내지 않는다.
선택 입력은 --problem, --solution, --next다. 각 본문 필드는 250자 한 줄로 제한하고
앞뒤 공백, 제어문자, 구분자, 백틱을 거부한다.

## 보완

record는 동일 날짜·프로젝트·STEP 재입력을 내용이 달라도 거부한다.
기존 기록을 보충·정정하려면 원문을 남기고 amend로 추가한다. 원본 실적이 없으면 거부한다.
amend도 프로젝트·STEP·작업·결과가 필요하며, 동일한 보완 문장을 반복 추가하지 않는다.

```powershell
python tools/mde_daily_log.py amend --date 2026-10-31 --project mde-core --step MDE-D2 --work "실제 개발일지 기능 구현" --result "재조회와 중복 방지도 확인" --solution "기존 기록 보존 확인"
```

보완은 원문 삭제나 시간 자동 합산을 하지 않는다. 조회는 날짜 파일의 전체 이력을 출력한다.
별도 id, 메타데이터 DB, 숨겨진 중복 저장소는 만들지 않는다.

## 보존과 오류 처리

STD-001의 오늘 작업·문제점·해결·내일 작업·소요시간 5개 제목과 순서만 허용한다.
잘못된 기존 구조는 변경하지 않고 거부한다. 입력값에 해당하는 한 줄을 각 제목 아래에 삽입한다.
기존 BOM, LF/CRLF, 빈 줄, D1 계획, 다른 실적과 수동 기록을 보존한다.
D1과 동일한 날짜별 잠금 파일을 사용하며 임시 파일 flush·fsync 후 원자적으로 교체한다.
쓰기 직전에 원본 변경 여부를 다시 확인해 감지된 외부 변경을 덮어쓰지 않는다.
비정상 종료로 잠금이 남으면 실행 중인 기록 작업이 없음을 확인한 뒤 잠금만 제거한다.
외부 수동 편집기는 이 잠금을 사용하지 않으므로 저장 도중 같은 일지를 편집하지 않는다.

조회는 파일을 만들지 않는다. 입력 오류·기존 기록 오류·파일 오류는 exit 1,
CLI 사용 오류는 exit 2, 성공 및 없는 날짜 안내는 exit 0이다.
Git 명령·Task 실행·TaskStore 생성·외부 통신을 운영 코드에서 호출하지 않는다.

## 실제 운영 검증

2026-10-31 실제 개발일지에 사용자 확인된 D1 이력과 이번 D2 구현 사실을 CLI로 기록한다.
입력값과 저장 내용, 재조회, 기존 내용 보존, 동일 입력 거부, 원문을 보존하는 보완을 확인한다.
자동 검사 통과와 사용자 직접 확인을 구분한다. D2의 사용자 최종 확인 전에는 자동으로 검증완료를 입력하지 않는다.
실제 명령·성공/실패 결과는 TEST-023에 기록한다.

## 검증 및 Git 명령

```powershell
uv run --frozen pytest tools/tests/test_mde_daily_log.py tools/tests/test_mde_daily_plan.py tools/tests/test_mde_daily_result.py -q
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen black --check .
uv run --frozen mde docs check
uv run --frozen mde docs check --target knowledge-guide
git diff --check
```

이번 STEP은 로컬 구현·실제 파일 운영 검사까지 수행하며 commit/push는 수행하지 않는다.
검토 후 사용할 커밋 명령은 다음과 같다.

```powershell
git add tools/mde_daily_log.py tools/tests/test_mde_daily_log.py docs/11_code/CODE-017-mde-actual-daily-log.md docs/12_test/TEST-023-mde-actual-daily-log.md docs/14_operations/DevelopmentLog/2026-10-31.md 11_AI_Request/2026-10-31-codex-mde-d2-actual-log.md
git commit -m "feat(mde): record actual daily development work"
```

## 다음 STEP

D2 사용자 실사용 확인 후 D3 TaskStore 연동을 재검토하고 D4 미완료 이월을 진행한다.
