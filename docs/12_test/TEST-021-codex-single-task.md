# TEST-021 MDE-CODEX-W1 단일 개발 작업

- 일자: 2026-10-21 (Asia/Seoul)
- 대상: CODE-015 / MDE-CODEX-W1
- 사전 조건: 기존 MDE Python 3.12.14 검증 환경, Git, 로그인된 codex-cli 0.163.0-alpha.10.2
- 판정: W1 필수 검증 PASS (실 CLI 한 건 포함)

## 절차와 예상 결과

실제 임시 Git 저장소에 HEAD를 준비하고 subprocess 대역으로 Codex 변경만 제어한다.
Git 조회 및 외부 validation은 실제 실행한다. 허용 경로만 변경하고 모든 명령이 성공하면
exit 0과 success=true, 실패·금지 경로·dirty tree는 exit 1과 실패 이유가 예상 결과다.
검증용 fixture의 초기 커밋과 금지 커밋 검출 테스트는 임시 Git 저장소에만 적용한다.
운영 runner에는 commit/push 명령이 없다.

검사 범위: 잘못된 JSON·필드·타입·timeout, Windows 경로와 디렉터리 경계,
dirty tree 보존, 허용/금지 파일, 검증 이후 변경, 실패 후 중단, CLI 누락·오류,
결과 경로 보호, 한글·공백 rename, HEAD 변경, 실제 timeout 자식 종료, 로그 redaction.
Windows 심볼릭 링크 생성 검사는 운영체제 권한 문제로 skip한다.

## 실제 Codex CLI acceptance

기존 MDE HEAD를 별도 로컬 복제본으로 만들고 clean 상태에서 시작한다.
실제 Codex에 문자열 공백 정리 함수와 의미 있는 pytest 테스트를 요청한다.
허용 파일은 `tools/automation/w1_example.py`, `tools/tests/test_w1_example.py` 둘이다.
외부 runner가 실제 pytest → Ruff → Black을 차례로 실행한다.
result의 success, changedFiles, disallowedFiles, 세 validation exit code와
실행 전후 HEAD 동일 여부를 검사한다. 복제본의 개발 결과는 운영 소스에 적용하지 않는다.

## 실제 결과

| 검사 | 실제 결과 |
|---|---|
| W1 대상 테스트 | 37 passed, 1 skipped, 9.39초 |
| MDE 루트 전체 | 318 passed, 1 skipped, 40.65초 |
| 앱·메타데이터 | 226 passed, 6.15초 |
| 전체 Black | 241 files unchanged, PASS |
| 전체 Ruff | PASS |
| 두 docs check | PASS |
| git diff --check | PASS |
| 실제 Codex LIVE-001 | exit 0, success=true |
| 실제 생성 파일 pytest | 9 passed |
| 실제 생성 파일 Ruff / Black | 각각 exit 0 |
| 허용 경로 | 두 파일만 변경, disallowedFiles=[] |

실행 전후 HEAD는 `1cd6d0628123dcad404dfc75f213f6e5e16c5943`으로 동일하다.
실 CLI 결과는 `result.live.json`, 요청은 `request.live.json`으로 검토 ZIP에 포함한다.
Codex가 내부 검증 도중 Black 실행 정체를 한 번 보고했으나, 외부 runner가 지정된
일반 Black 명령을 별도로 실행해 exit 0을 확인했다. 실패 자동수정 반복은 사용하지 않았다.
첫 단위 검사에서는 테스트 fixture의 __pycache__가 untracked가 되어 사후 경로 검사에
걸렸다. fixture에 실제 MDE와 같은 cache ignore를 설정해 바로잡았다.
초기 기본 .venv의 dev 도구 누락도 기존 검증 환경을 선택하여 해결했다.

추가 검사 중 경고는 보고되지 않았다. 기존 Provider, Workflow, task_runner,
pyproject 및 lock 파일의 Git diff는 없다. 검증 단계에서는 생산 저장소 commit/push/save 및
서비스 배포를 수행하지 않았다. W1 소스의 GitHub 반영은 이후 사용자의 별도 요청에 따른다.

## 재실행

CODE-015의 명령을 따른다. 이번 PC에서는 기본 `.venv`에 dev 도구가 없어 이전 STEP의
`work/mde-audit-root-env`를 UV_PROJECT_ENVIRONMENT로 지정하여 frozen uv 명령을 사용한다.
실 CLI acceptance 결과와 요청·출력은 이번 작업의 검토 산출물에 보관한다.
