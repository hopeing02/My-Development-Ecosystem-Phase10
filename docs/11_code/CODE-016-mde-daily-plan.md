# CODE-016 STEP MDE-D1 — 기존 앱 일일 개발계획

- 일자: 2026-10-29 (Asia/Seoul)
- 기준: AGENTS.md, DEV-001, STD-001, docs/development-guidelines의 8개 지침
- 입력 명세: 첨부 MDE_STEP_D1_Phase10_Files.zip
- 저장소 기준: main / e6d389e
- 검증 기록: [TEST-022](../12_test/TEST-022-mde-daily-plan.md)

## 변경사항과 최소 설계

현재 저장소의 앱 목록 조회, 날짜별 계획 한 건 등록, 등록 계획 조회를 표준 라이브러리 CLI로 제공한다.
확인한 앱은 autoknowledge-lite, document-parser, knowledge-viewer,
yeominjeon-auto-recharge다. sample-project는 제외한다. 메타데이터 유무나 draft 상태로 제외하지 않는다.
앱 이름은 하드코딩하지 않고 실제 apps/ 디렉터리에서 조회한다.

원본은 기존 DevelopmentLog/YYYY-MM-DD.md 한 곳에 둔다.
새 일지는 STD-001의 다섯 제목만 만들고 실제 소요시간은 미계측으로 남긴다.
기존 일지는 오늘 작업 제목 바로 아래 계획 한 줄만 추가한다.
동일 날짜 두 번째 등록은 거부하며 수정·삭제 명령은 이번 범위에 없다.

## 기존 재사용 함수와 신규 코드 필요성

기존 mde.logging.logger, mde.agent.lock, CheckpointStore,
knowledge.document_writer의 실제 소스를 확인했다. 일일 계획 조회·등록 함수는 없다.
AgentLock은 에이전트 실행용 잠금이고 DocumentWriter는 YAML 메타데이터·지식 문서를
재구성하는 계약이므로 이 STEP의 원본 일지 보존에 그대로 사용할 수 없다.
직접 import한 기존 운영 함수는 없다. 기존 일지 경로·기록 표준과 첨부 코드 초안을 활용한다.
기존 함수와 공통 Core를 수정하거나 복사하지 않는다.

- 신규 운영 모듈: tools/mde_daily_plan.py
- 신규 함수: list_app_projects, validate_day, daily_log_path, register_plan, show_plan, main
- 신규 함수 이유: 현재 STEP의 앱 확인·입력 검증·일지 경로·등록·조회·CLI 진입점에 각각 필요하다.
- 신규 검증 모듈: tools/tests/test_mde_daily_plan.py
- 수정 운영 함수: 없음
- 문서 동기화: tools/README, CHANGELOG의 Unreleased, CODE-016, TEST-022, 개발일지, AI 요청서

## 첨부 초안에서 보완한 점

날짜는 함수 직접 호출에도 검증한다. STEP은 영문·숫자로 시작하는 1~64자의
영문·숫자·점·밑줄·하이픈이고, 목표는 공백 정리 후 1~200자 한 줄이다.
목표의 줄바꿈·제어문자를 거부하며 예정 시간은 정수 15~720분이다.
출력 경로가 링크를 통해 저장소 밖을 가리키면 거부한다.

기존 일지는 바이트로 읽어 UTF-8 BOM, LF/CRLF와 나머지 내용을 보존한다.
제목 정규식은 빈 줄까지 삼키지 않는다. 기존 일지 변경은 같은 디렉터리의 임시 파일에
쓰기·flush·fsync 후 os.replace로 교체해 쓰기 실패 시 원본을 보존한다.
새 일지는 배타 생성 모드로 열어 이미 존재하는 파일을 덮어쓰지 않는다.
날짜별 배타 잠금 파일을 사용해 이 CLI의 동시 등록 중 하나만 성공시킨다.

## 실행 및 테스트 명령

저장소 루트에서 실행한다. 아래 plan 명령은 사용 예시이며 사용자의 실제 계획이 아니다.
날짜 생략 시 실행 PC의 오늘 날짜, 시간 생략 시 120분이다.

```powershell
python tools/mde_daily_plan.py projects
python tools/mde_daily_plan.py plan --project document-parser --step DOC-PARSER-2 --goal "다음 파서 검증 범위 확인" --minutes 120 --date 2026-10-30
python tools/mde_daily_plan.py show --date 2026-10-30
python -m unittest discover -s tools/tests -p "test_mde_daily_plan.py" -v

uv sync --frozen
uv run --frozen pytest tools/tests/test_mde_daily_plan.py -q
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen black --check .
uv run --frozen mde docs check
uv run --frozen mde docs check --target knowledge-guide
git diff --check
```

성공 종료 코드는 0이다. 조회 대상이 없으면 안내와 0을 반환한다.
입력 검증·파일 오류는 stderr의 오류 메시지와 1, argparse 사용 오류는 2다.
런타임은 외부 서비스·AI API·별도 DB를 요구하지 않는다.
계획을 TaskStore나 Workflow에 연결하지 않고 Git 명령을 실행하지 않는다.

## 기존 기능 영향과 미해결 범위

기존 앱·TaskStore·Workflow·에이전트·Git 기능, 의존성 및 lock 파일은 변경하지 않는다.
사용자의 실제 앱별 목표·STEP이 지정되지 않아 실제 일지에 예시 계획을 임의 등록하지 않는다.
개발 검증은 자동화 시험이며 사용자 실사용 확인은 별도다.

프로세스 강제 종료 시 .md.d1-lock이 남을 수 있다. 진행 중인 등록이 없음을 확인한 뒤
그 잠금 파일만 제거한다. 외부 편집기는 이 잠금을 사용하지 않으므로 등록과 수동 편집을
동시에 하지 않는다. Git 추적 일지에 비공개 업무자료나 민감정보를 작성하지 않는다.

## 검토 후 사용할 Git 커밋 명령

검증 결과와 변경 파일을 확인한 뒤 실행한다.

```powershell
git add tools/mde_daily_plan.py tools/tests/test_mde_daily_plan.py tools/README.md CHANGELOG.md docs/11_code/CODE-016-mde-daily-plan.md docs/12_test/TEST-022-mde-daily-plan.md docs/14_operations/DevelopmentLog/2026-10-29.md 11_AI_Request/2026-10-29-codex-mde-d1.md
git commit -m "feat(mde): add existing-app daily plan CLI"
```

## 다음 STEP

MDE-D2 — 기존 Task 실행 결과와 검증 상태를 일일 계획에 연결.
D1 실사용 확인 후 별도 STEP으로 진행한다.
