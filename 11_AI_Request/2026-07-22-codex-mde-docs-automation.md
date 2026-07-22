# Codex AI 요청서

- 요청 ID: mde-docs-automation
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

MDE 전체 사용법을 중앙 문서로 제공하고 실제 CLI 변경에 맞춰 안전하게 정정·추가·삭제할 수 있게 한다.

## 요청 내용

- MDE 전체 사용자 가이드 작성
- `mde docs check` 구현
- `mde docs update` 변경 미리보기 구현
- `mde docs update --apply` 승인 기반 적용 구현
- 테스트, ADR, QA, CODE, TEST, Change Log, DevelopmentLog 기록
- Knowledge 재색인과 검색 검증

## 제약 조건

- Knowledge Plugin의 원본 보호 원칙을 유지한다.
- 전체 문서를 무인으로 덮어쓰지 않는다.
- 설명 본문과 관리 구간을 분리한다.
- 자동 commit과 push를 구현하지 않는다.
- 표식 오류가 있으면 문서를 수정하지 않는다.
- 테스트 없이 완료 처리하지 않는다.

## 기대 결과

실제 MDE CLI를 기준으로 전체 사용법의 관리 구간을 검사하고, 사용자가 diff를 검토한 뒤 명시적으로 적용할 수 있다.
