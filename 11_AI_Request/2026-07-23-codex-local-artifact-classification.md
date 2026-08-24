# AI 요청서

- 요청 ID: AIR-2026-07-23-003
- 작성일: 2026-07-23
- 대상 AI: Codex
- 목적: MDE 로컬 미추적·삭제 항목 분류와 안전한 Git 제외
- 처리 상태: Completed

## 요청 내용

Android, runtime, test dependencies, local data, 이전 Vault, 첨부·incoming, heartbeat와 추적 파일 삭제를 분석해 커밋·제외·복구 보관·사용자 결정 필요 항목으로 분류한다.

## 제약 조건

- 파일을 삭제하거나 이동하지 않는다.
- 개인 콘텐츠와 로컬 SDK 경로를 커밋하지 않는다.
- Android 전체 폴더를 제외해 미래 소스를 숨기지 않는다.
- 기존 `agent-test-target.txt` 삭제를 수정하거나 커밋하지 않는다.
- ADR·TEST·DevelopmentLog와 Changelog를 기록한다.

## 기대 결과

- 경로별 분류표
- 최소 범위 `.gitignore` 규칙
- 원본 보존과 Git 상태 정리 검증
