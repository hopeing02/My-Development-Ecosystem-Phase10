# CODE-013 현재 PC 로컬 FastAPI 배포

- 일자: 2026-10-19 (Asia/Seoul)
- 기준 커밋: `3193b41b98928453a6b827b01a4acf7c33a930a7`
- 사용자 지정 대상: 현재 PC의 로컬 FastAPI 서비스
- STEP 상태: 구현 및 자동 검증 PASS
- 전체 실 AI 개발·운영 배포 상태: 실 AI 실행 방식 선택 및 live 검증 전

## 변경과 재사용

신규 deployment.py 1개가 Git snapshot, 후보 시작, 프로세스 소유·생성 시각·listen·
health 확인, state 원자 교체, 이전 버전 선택과 종료를 담당한다. 기존 Git 경계,
TaskExecutionLock, Uvicorn, runtime Plugin/CommandRegistry를 재사용했다.
기존 PowerShell supervisor는 앱 전용이어서 교체하지 않았다. CLI deploy는 local,
status, rollback, stop을 제공한다. psutil 7.2.2는 PID 재사용 및 자식 프로세스 종료를
검증하기 위해 필요한 유일한 새 runtime 의존성이다. 기존 제3자 버전은 유지했다.

새 feature-local.yaml은 기본 feature와 Task를 변경하지 않고 실제 테스트·커밋·선택적
push·로컬 배포를 연결한다. workflow run의 --inputs와 --max-fix-attempts는 기존
execute_workflow_with_fix_loop를 호출한다. push 기본값은 false이며 true 요청 시
별도 Git 인증이 필요하다. dry run은 프로세스·파일을 변경하지 않는다.

배포 handler는 성공한 실제 테스트 결과와 현재 HEAD에 해당하는 Workflow commit을
요구한다. 일반 deploy CLI는 검증한 커밋을 명시적으로 실행하는 사용자 경계다.
Task 엔진의 Git 비활성화·외부 Sync 책임은 그대로다. 새 Workflow를 Task의 기존 Git
정책에 우회 연결하지 않는다.

## 배포 전 발견한 리뷰 오류 제거

기존 AIWorkflowPlugin.review는 무조건 approved=True였다. 자동 배포 연결의 선행
오류이므로 응답 metadata의 명시적 boolean만 받도록 수정했다. 거절·누락·문자열
판정은 적용 전에 중단한다. 실제 생성 artifact 내용을 리뷰 context에 넣고 HTTP
provider prompt에도 전달한다. MockAIProvider만 테스트용 명시적 승인을 제공한다.
기존 응답 구조·provider registry를 재사용했으며 새 AI Framework는 없다.

## 신규 파일 필요성

- deployment.py: 기존에 없던 범용 로컬 snapshot 배포·lifecycle 경계.
- feature-local.yaml: 기본 검증 완료 Workflow를 유지하는 명시적 로컬 배포 경로.
- test_local_deployment.py: 실제 프로세스·실패 복구·CLI 검증을 임시 서비스로 분리.
- ADR-020 및 CODE·TEST: 입력·출력 계약과 구현·검증 기록.

나머지는 기존 함수·테스트·문서·lock을 최소 수정했다. 신규 앱이나 MDE 저장소를
새로 만들지 않았다. 기존 AutoKnowledge 앱의 API·저장 형식·원본 Vault는 수정하지 않았다.

## 실행

`docs/05_commands/CMD-004-mde-user-guide.md`의 로컬 배포 예제를 따른다.

```powershell
uv run mde deploy local --app package.api:app --app-dir src --python <python.exe> --health-path /health
uv run mde deploy status
uv run mde deploy rollback
uv run mde deploy stop
uv run mde workflow run feature-local --runtime --inputs .mde/inputs.json --max-fix-attempts 2
```

기존 환경변수는 자식에 상속되지만 state에는 저장하지 않는다. 코드 snapshot은 Git에
추적된 커밋만 사용한다. 데이터·Vault는 snapshot 밖의 고정 경로를 사용해야 한다.
실제 AutoKnowledge 로컬 배포는 전용 runtime data/Vault 경로로 분리해 원본을 보존한다.
실행 주소와 실제 서비스 상태는 최종 작업 보고서에서 확인한다.

## 결과와 기존 기능 영향

자동 검증은 TEST-019를 따른다. 실제 pytest·Git·FastAPI 프로세스를 사용하고 AI만
결정적 대역으로 제어해 실패→수정→테스트→커밋→임시 bare push→배포→HTTP 응답까지
확인했다. 별도 공개 CLI 입력 JSON 경로도 검증했다. wheel에 신규 모듈과 YAML이 포함된다.
필수 검증은 모두 통과했다. 리뷰 응답의 approved 누락은 이제 안전하게 실패하므로
실 provider는 문서화한 계약을 충족해야 한다.

## 제한·미해결·다음 STEP

- 배포마다 새 loopback URL이다. 고정 URL 프록시·로그인 자동 시작은 구현하지 않았다.
- rollback은 살아 있는 직전 프로세스를 선택한다. 데이터 migration·DB rollback은 없다.
- 이전 정상 프로세스 1개를 유지하며 더 오래된 소유 프로세스는 다음 승격 시 종료한다.
  종료에 실패한 레코드는 retired에 남겨 stop에서 재시도한다. snapshot·로그는 보존한다.
- 의존성 설치·검증 환경은 배포 전에 준비한다. release별 별도 venv를 만들지 않는다.
- 실제 AI 선택·인증·코드/실패 로그 문맥과 live end-to-end 검증은 남아 있다.
- Viewer·Android·실기기 검증은 이번 Python 배포 STEP에서 재실행하지 않았다.

다음은 실제 AI 실행 방식을 연결하고 작은 기능 요청 한 건으로 전체 경로를 검증하는
것이다. 구현 선택 질문은 사용자에게 제시했다. 새 프레임워크는 도입하지 않는다.

## Git

필수 검증 통과 후 별도 커밋·fast-forward 원격 반영한다.
메시지: `feat(deploy): add local FastAPI deployment workflow with health and rollback`.
최종 SHA와 전체 변경 파일은 작업 보고서·검토 ZIP에 기록한다.

## 근거

- [psutil 프로세스 API](https://psutil.io/api/psutil.html)
- 실제 설치된 Uvicorn CLI와 psutil 7.2.2를 사용한 프로세스 통합 테스트

## 실배포 보완

현재 PC의 전체 monorepo snapshot 추출에서 Windows MAX_PATH 제한을 발견했다.
기존 경로 이탈 검사를 유지하고 Windows 추출 대상에만 확장 경로를 사용한다.
Android 파일을 누락시키거나 기존 소스를 변경하지 않는다. 긴 경로 회귀를 추가했다.
