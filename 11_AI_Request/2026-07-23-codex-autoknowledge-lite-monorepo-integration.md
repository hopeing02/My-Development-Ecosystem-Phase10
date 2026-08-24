# Codex AI 요청서

- 작성일: 2026-07-23
- 대상: Codex
- 프로젝트: autoknowledge-lite

## 요청

별도 `.runtime/autoknowledge-lite/` 저장소의 실행 가능한 Python·Android 구현을 MDE 모노레포의 `apps/autoknowledge-lite/`로 통합한다.

## 필수 조건

- 개인 Vault와 프로젝트 공식 문서를 분리한다.
- 프로젝트 문서는 `docs/15_projects/autoknowledge-lite/`를 단일 원본으로 한다.
- 개인 Vault, 작업 JSON, 실행 로그, 비밀값, 가상환경, 빌드 결과를 복사하지 않는다.
- 현재 Vault Git 동기화 설정은 변경하지 않는다.
- 별도 저장소는 검증 완료 전까지 삭제하지 않는다.
- 구현·테스트·사용법·ADR·DevelopmentLog·CHANGELOG 기록 규칙을 따른다.
- Python·Android·MDE 회귀 테스트를 실행한다.

## 완료 기준

- 메인 앱 경로에서 서버와 Android 프로젝트가 빌드·테스트된다.
- 로그인 자동 시작 작업이 통합된 메인 앱 경로를 사용한다.
- 개인 Vault와 프로젝트 문서의 기존 내용 및 저장 경계가 보존된다.
