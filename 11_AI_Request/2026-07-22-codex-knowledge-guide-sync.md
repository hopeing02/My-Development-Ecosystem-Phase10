# Codex AI 요청서

- 요청 ID: knowledge-guide-sync
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

Knowledge Plugin 상세 가이드의 명령 참조도 실제 CLI와 안전하게 동기화한다.

## 요청 내용

`knowledge-guide` target을 추가하고 `CMD-003`의 관리 구간에서 Knowledge 명령·옵션을 자동 검사·미리보기·승인 적용할 수 있게 한다.

## 제약 조건

- 상세 설명 본문은 자동 수정하지 않는다.
- 정확한 관리 표식 사이만 수정한다.
- 기본 동작은 읽기 전용이어야 한다.
- 자동 commit과 push를 수행하지 않는다.
- 테스트 없이 완료 처리하지 않는다.

## 기대 결과

`mde docs check --target knowledge-guide`와 `mde docs update --target knowledge-guide --apply`가 동작하고, MDE 전체 가이드와 Knowledge 상세 가이드를 독립적으로 관리할 수 있다.
