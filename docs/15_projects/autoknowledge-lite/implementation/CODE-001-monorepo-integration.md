# CODE-001 AutoKnowledge Lite 모노레포 통합

- 작성일: 2026-07-23
- 상태: Complete

## 구현

- 별도 저장소에서 Git이 추적하던 Python·Android 소스 31개를 `apps/autoknowledge-lite/`로 통합했다.
- FastAPI, 분석기, 콘텐츠 수집, Markdown, Vault 저장, Git 동기화 구현과 테스트를 공식 앱 경로로 옮겼다.
- Android Gradle 구성, 공유 대상, 클립보드 저장 및 payload 테스트를 통합했다.
- 앱 전용 `pyproject.toml`과 `uv.lock`으로 실행 환경을 재현할 수 있게 했다.
- 기본 작업 JSON 경로를 현재 작업 폴더가 아닌 앱 패키지 기준 `data/`로 고정했다.
- Windows 로그인 자동 시작 스크립트를 공식 앱 경로에 추가하고 예약 작업 대상을 전환했다.

## 제외 및 보존

- 개인 Vault, 작업 JSON, 실행 로그, 가상환경, 빌드 결과는 소스 통합 대상에서 제외했다.
- Vault Git 동기화 환경값과 원격 저장소는 변경하지 않았다.
- 별도 `.runtime/autoknowledge-lite/` 저장소는 자동 삭제하지 않고 복구용으로 보존했다.
- 프로젝트 공식 문서는 중앙 `docs/15_projects/autoknowledge-lite/`만 사용한다.

## 관련 문서

- `../../../../09_decisions/ADR-011-autoknowledge-lite-monorepo-integration.md`
- `../tests/TEST-001-monorepo-integration.md`
- `../usage/GUIDE-001-usage.md`
