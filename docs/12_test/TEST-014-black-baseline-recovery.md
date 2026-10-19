# TEST-014 Black 서식 기준 복구 회귀검증

- 일자: 2026-10-19 (Asia/Seoul)
- 대상: CODE-007의 기존 수정과 CODE-008의 서식 정리
- 판정: PASS / 개발 재개 환경·패키지·서식 복구 STEP 검증 통과
- 범위: Python 유지보수 검증. 모바일 RC 재승인 또는 새 릴리스 판정이 아님.

## 사전 조건과 절차

Python 3.12.14, Black 26.10.1, Ruff 0.15.20, uv 0.13.1을 사용했다.
루트와 앱은 각각의 lock으로 구성한 격리 환경을 재사용했다. 외부 AI API 호출,
개인 Vault 변경, 운영 Agent 실행, save·commit·push는 수행하지 않았다.
실행 명령은 `../11_code/CODE-008-black-baseline-recovery.md`에 기록했다.

## 서식 변경 검증

| 대상 | 기대 | 실제 |
|---|---|---|
| 도구 10개 | AST·주석 동일 | PASS |
| 실행 모듈 37개 | AST·주석 동일 | PASS |
| 테스트·앱 20개 | AST·주석 동일 | PASS |
| 전체 Black | 서식 변경 필요 0개 | 234 files would be left unchanged, exit 0 |
| 전체 Ruff | 오류 0개 | All checks passed, exit 0 |

AST는 `ast.dump(ast.parse(source), include_attributes=False)`로 비교했다.
주석은 tokenize의 COMMENT 토큰 문자열 목록을 순서대로 비교했다.
Black 자체 검증과 별도로 제안 적용 전과 실제 파일 적용 후 모두 동일성을 확인했다.
서식 확인을 위해 원본과 결과 파일 SHA-256, 그룹, 검증 상태를 JSON 명세로 제공한다.

## 회귀 및 정합성 검증

| 검증 | 실제 결과 |
|---|---|
| 루트 전체 pytest | 215 passed, 경고 1개, 14.67초 |
| 앱 전체 + 메타데이터 테스트 | 224 passed, 경고 6개, 5.40초 |
| 루트 lock --check | PASS |
| 앱 lock --check | PASS |
| git diff --check | PASS |

앱 자체 테스트는 218개다. 메타데이터 6개는 루트 실행에도 포함되므로 합산하지 않는다.
경고는 기존 Starlette deprecation 경고다. 실패·skip·xfail은 이번 실행에서 없었다.

## 미검증과 기존 승인 범위

Viewer·Android·APK·실기기 검증은 재실행하지 않았다. 관련 소스 수정이 없으므로
이번 Python 서식 STEP의 검증 범위에서 제외했으며 기존 실기기 승인을 새로 주장하지
않는다. 새 검증 제외 설정이나 기존 테스트 축소는 추가하지 않았다.

## 남은 문제

생성 egg-info의 Git 추적 문제와 deprecation 경고는 별도 과제로 남긴다.
이번 STEP에서 확인한 필수 검증 실패는 없다. 자동 커밋·push는 수행하지 않았다.
