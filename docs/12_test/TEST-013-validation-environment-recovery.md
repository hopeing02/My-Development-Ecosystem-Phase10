# TEST-013 개발 재개 검증 환경 및 패키지 정합성

- 일자: 2026-10-19 (Asia/Seoul)
- 기준: `3aa9ac3`에 대한 로컬 변경
- 최종 판정: FAIL / STEP 미완료 / save·commit·push 보류

> 이 문서의 판정은 초기 검증 결과다. 2026-10-19 후속 작업의 전체 검증 PASS는
> `TEST-014-black-baseline-recovery.md`에 기록했다. 초기 실패 근거는 삭제하지 않는다.

## 사전 조건과 방법

Python 3.12.14, 루트·AutoKnowledge Lite별 격리 환경, 각 프로젝트의 frozen lock을
사용했다. 원격 Git push, Agent 자동 실행, 실제 개인 Vault 변경은 수행하지 않았다.
실행 명령은 `../11_code/CODE-007-validation-environment-recovery.md`를 따른다.

## 회귀 재현

버전 수정 전 새 메타데이터 테스트에서 `0.6.0 != 0.10.0`으로 1 failed, 5 passed를
확인했다. 이전 분석에서 앱 설치 distribution은 0.6.0, 런타임은 0.10.0이었다.
수정 후 루트와 앱 환경 모두 저장소 밖 isolated 프로세스의 버전 일치 테스트를 통과했다.

## 실제 결과

| 검증 | 결과 |
|---|---|
| 루트 전체 pytest | 215 passed, Starlette 경고 1개 |
| 앱 전체 + 메타데이터 6개 테스트 | 224 passed, Starlette 경고 6개 |
| 전체 Ruff | PASS |
| 변경 Python 테스트 파일 Black 검사 | PASS |
| 전체 Black 검사 | FAIL: 67 files would be reformatted, 167 unchanged |
| 루트 lock 정합성 검사 | PASS |
| 앱 lock 정합성 검사 | PASS |
| 기존 Workflow 목록 | bugfix/docs/feature/refactor 정상 |

루트 215개에는 메타데이터 테스트 6개가 포함되며, 앱 검증 224개에도 같은 6개를
다른 설치 환경에서 재실행했다. 두 숫자를 독립 테스트 총합으로 합산하지 않는다.
앱 자체 회귀는 218개다.

## 기대 결과와 판정

의존성 선언·lock·설치 메타데이터·런타임의 정합성과 기존 Python 회귀는 통과했다.
전체 Black 검사는 기대한 exit 0을 얻지 못했다. 따라서 필수 검증 전체 통과로
표현하지 않으며, 완료·save·commit·push 대상으로 처리하지 않는다.

## 미검증 및 후속

Viewer·Android JVM·APK·실기기 검증은 재실행하지 않았다. 해당 기능 수정은 없다.
기존 67개 파일의 서식 불일치 및 추적 중인 생성 메타데이터 문제는 남아 있다.
검증 제외 규칙이나 테스트 축소는 추가하지 않았다.
