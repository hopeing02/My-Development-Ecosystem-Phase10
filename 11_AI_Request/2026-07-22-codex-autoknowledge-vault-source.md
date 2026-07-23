# Codex AI 요청서

- 요청 ID: autoknowledge-vault-source
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

AutoKnowledge가 생성한 개인 Markdown Vault를 MDE Knowledge Plugin에 안전하게 연결한다.

## 요청 내용

`autoknowledge-vault`를 `personal`, `obsidian` Source로 사용자 전역 Registry에 등록하고 첫 스캔, Source 제한 검색, 증분 재스캔, 민감 Source 기본 제외, 감사 로그 개인정보 보호를 검증한다.

## 제약 조건

- Vault 원본을 수정·삭제·이동하지 않는다.
- Source 경로를 Git 관리 문서에 기록하지 않는다.
- `sensitive=true`, `allow_agent_access=false`를 유지한다.
- 기본 검색과 `--all` 검색에서 민감 Source를 제외한다.
- 외부 전송, 자동 commit, 자동 push를 수행하지 않는다.

## 기대 결과

개인 Vault가 사용자 로컬 SQLite에만 색인되고 명시적인 Source 제한 검색으로만 조회되며, 원본과 보안 경계가 유지된다.
