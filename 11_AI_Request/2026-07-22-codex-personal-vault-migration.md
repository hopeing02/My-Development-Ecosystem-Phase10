# Codex AI 요청서

- 요청 ID: personal-vault-migration
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

AutoKnowledge 개인 Git Vault를 MDE 코드 저장소 밖의 사용자 전용 경로로 안전하게 이전한다.

## 요청 내용

기존 Vault의 Git 상태를 확인하고 `.git`을 포함한 전체 복사, 파일 해시와 Git 무결성 검증, MDE Source 경로 전환, 스캔·검색·보안·감사 로그 확인을 수행한다.

## 제약 조건

- 기존 Vault를 삭제하거나 이동하지 않는다.
- 복사본 검증 전에는 Source를 전환하지 않는다.
- 개인 Source 보안 기본값을 유지한다.
- 절대경로를 Git 관리 기록에 그대로 남기지 않는다.
- Git commit, push, 외부 동기화를 수행하지 않는다.
- AutoKnowledge 과거 JSON 기록은 수정하지 않는다.

## 기대 결과

활성 개인 Vault가 MDE 저장소 외부의 독립 Git 저장소가 되고, 원본과 복구 가능성을 보존하면서 MDE Knowledge 검색이 새 경로에서 정상 동작한다.
