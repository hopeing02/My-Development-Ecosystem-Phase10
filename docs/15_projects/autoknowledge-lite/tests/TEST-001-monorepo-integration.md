# TEST-001 AutoKnowledge Lite 모노레포 통합

- 작성일: 2026-07-23
- 상태: Passed

## 목적

별도 런타임 저장소의 실행 가능한 AutoKnowledge Lite 코드가 `apps/autoknowledge-lite/`에서 동일하게 동작하고, 개인 Vault와 프로젝트 문서 경계가 유지되는지 검증한다.

## 결과

| 구분 | 결과 |
|---|---|
| 앱 Python 테스트 | 30 passed |
| 앱 Ruff check | 통과 |
| 앱 Ruff format check | 16 files formatted |
| Android 단위 테스트 | 통과 |
| Android Debug APK | BUILD SUCCESSFUL |
| MDE 전체 회귀 | 146 passed |
| mde-docs 증분 스캔·검색 | Added 3, Updated 11, Errors 0, 통합 문서 검색 성공 |
| 저장소 전체 Ruff check | 통과 |
| 저장소 전체 formatter | 기존 52개 파일 포맷 부채로 실패, 통합 앱 파일은 통과 |
| type check | 별도 type checker 설정 없음 |
| 상태 API | `service=autoknowledge-lite`, `status=ok`, `version=0.1.0` |
| 자동 시작 | 공식 앱 스크립트로 실행 확인 |
| Vault·Git 설정 | 파일 해시와 사용자 환경값 무변경 확인 |

## 참고 경고

- FastAPI TestClient의 외부 라이브러리 사용 중단 예고 경고 1건
- Windows pytest 캐시 디렉터리 생성 권한 경고

두 경고는 테스트 결과와 앱 동작에 영향을 주지 않는다.

## 저장 경계 검증

- 외부 Personal Vault와 현재 설정된 AutoKnowledge Vault의 원본 파일을 수정하지 않았다.
- 개인 Vault, 작업 JSON, 실행 로그와 Android 빌드 결과는 Git 추적 대상에 포함되지 않는다.
- 프로젝트 개발 문서는 `docs/15_projects/autoknowledge-lite/`에만 기록했다.
- 실제 Git 원격을 사용하는 테스트는 실행하지 않았고 Git 동기화 단위 테스트는 subprocess 테스트 대역을 사용했다.
