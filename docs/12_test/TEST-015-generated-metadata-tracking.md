# TEST-015 생성 패키지 메타데이터 추적 정리

- 일자: 2026-10-19 (Asia/Seoul)
- 대상: CODE-009, 기존 ADR-010 적용
- 판정: PASS

## 회귀 재현

새 테스트를 추적 정리 전에 실행해 1 failed, 6 passed를 확인했다. 원인은
`git ls-files -- '*.egg-info/*'`가 생성 파일 6개를 반환한 것이다.
추적 해제 후 동일 테스트 파일은 7 passed였다.

## 보존·재설치 검증

- `git rm --cached` 전후 로컬 파일 6개의 SHA-256 동일.
- 파일 6개는 로컬에 유지되며 기존 `.gitignore` 30행의 규칙에 일치.
- 전체 egg-info 추적 항목: 0개.
- 루트 패키지 frozen 강제 재설치: PASS.
- 앱 경로 mde-core frozen 강제 재설치: PASS.
- 각각의 재설치 전후 `git status --porcelain=v1 -uall` 출력이 동일.
- 각 격리 환경에서 저장소 밖 isolated Python import 및 설치 메타데이터 버전:
  모두 0.10.0.
- 각 환경의 `python -I -m mde.cli --help`: exit 0, 정상 도움말.

두 설치 경로는 Python 3.12.14를 사용했다. 실제 검증에는 프로젝트 밖의 별도 가상환경을
재사용했다. 검증 작업은 개인 Vault·운영 Agent·외부 AI API를 사용하지 않았다.

## 전체 검증 결과

| 항목 | 결과 |
|---|---|
| 루트 pytest | 216 passed, 기존 Starlette 경고 1개 |
| 앱 + 메타데이터 pytest | 225 passed, 기존 Starlette 경고 6개 |
| Black 전체 | 234 files would be left unchanged, exit 0 |
| Ruff 전체 | All checks passed, exit 0 |
| diff / cached diff 검사 | PASS |

앱 테스트는 자체 218개와 메타데이터 7개다. 메타데이터 검사는 루트 실행에도 포함되므로
두 테스트 수를 독립 총합으로 합산하지 않는다.

## 범위와 미해결 문제

업무 로직 변경은 없고, 새 런타임 코드나 의존성은 없다. Viewer·Android·APK·실기기
검증은 재실행하지 않았다. Starlette 경고는 기존 상태로 남아 있으며 테스트 실패는
없다. 실제 Git 원격 반영 결과는 후속 작업 결과 보고서를 따른다.
