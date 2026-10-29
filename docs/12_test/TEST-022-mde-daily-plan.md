# TEST-022 MDE-D1 일일 개발계획

- 일자: 2026-10-29 (Asia/Seoul)
- 대상: CODE-016 / tools/mde_daily_plan.py
- 사전 조건: Windows, Python 3.12.14, 저장소 uv.lock 기준 frozen 개발 환경
- 판정: D1 자동 검증 및 기존 기능 회귀 PASS, 사용자 실사용 확인 전

## 절차와 예상 결과

실제 운영 CLI를 subprocess로 실행하고 표준 라이브러리 함수도 직접 호출한다.
파일 변경 검사는 TemporaryDirectory에서 수행한다.

1. 네 앱을 이름순으로 조회하고 sample-project와 일반 파일을 제외한다.
2. 새 일지에 계획을 등록·조회하고 다섯 제목·기본 120분·실제 미계측을 확인한다.
3. 같은 날짜 중복·동시 등록을 거부하고 기존 파일 바이트를 보존한다.
4. 기존 일지의 BOM, LF/CRLF, 빈 줄, 본문을 한 줄 추가 외에는 그대로 보존한다.
5. 잘못된 날짜·경로·프로젝트·STEP·목표·시간은 실패하며 일지를 생성하지 않는다.
6. 존재하지 않는 일지·계획 조회는 안내와 exit 0이며 파일을 만들지 않는다.
7. 기존 제목 누락·교체 실패·기존 잠금에서 원본 보존과 임시 파일 정리를 확인한다.
8. 미래 날짜·윤년·시간 경계값·저장소 밖 링크 차단을 확인한다.

실제 저장소에서는 projects/show 조회를 실행한다. 사용자의 실제 목표가 지정되지 않았으므로
예시 계획으로 운영 일지를 채우지 않는다. 전체 루트 pytest, Ruff, Black, 관리 문서 두 가지 검사로
기존 기능 회귀를 확인한다. 재실행 명령은 CODE-016에 있다.

## 실제 결과

| 검사 | 실제 결과 |
|---|---|
| uv sync --frozen | PASS, 기존 uv.lock과 pyproject 변경 없음 |
| D1 pytest | 18 passed, 37 subtests passed, 2.40초 |
| D1 표준 unittest | 18 tests OK, 2.539초 |
| 루트 전체 pytest | 338 passed, 1 skipped, 37 subtests passed, 53.36초 |
| 전체 Ruff | All checks passed |
| 전체 Black | 249 files unchanged, PASS |
| mde docs check | PASS |
| mde docs check --target knowledge-guide | PASS |
| git diff --check | PASS |
| 실제 저장소 projects | 네 앱 이름순 조회, sample-project 제외 |
| 실제 저장소 show --date 2026-10-29 | D1 개발계획 없음 안내, exit 0 |
| 실제 2026-10-21 개발일지 복사본 왕복 | 계획 등록·조회 성공, 삽입 한 줄 외 바이트 동일, 원본 파일 변경 없음 |

전체 pytest의 skip 1건은 기존 W1의 Windows 심볼릭 링크 권한 검사다.
D1의 저장소 밖 링크 차단 검사는 이 PC에서 실행되어 통과했다.
경고·실패는 보고되지 않았다. 기존 앱·packages·의존성·상위 개발지침의 변경은 없다.
운영 사용자 계획을 임의 등록하거나 D2 연결, 서비스 배포, Git commit/push를 수행하지 않았다.

검증 도구는 작업 폴더의 저장소 밖 전용 환경에 설치했다.
UV_PROJECT_ENVIRONMENT로 해당 환경을 지정하고 frozen 명령을 사용했다.
표준 unittest 검사도 같은 Python 3.12.14에서 실행했다.
