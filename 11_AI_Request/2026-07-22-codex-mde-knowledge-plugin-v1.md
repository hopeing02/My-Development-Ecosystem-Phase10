# MDE Knowledge Plugin v1 구현 요청

- 요청 ID: MDE-KNOWLEDGE-PLUGIN-V1-20260722
- 작성일: 2026-07-22
- 대상 AI: Codex
- 처리 상태: Completed

## 목적

MDE 안에 작고 안전한 로컬 Knowledge Plugin을 구현한다.

## 요청 내용

개발·프로젝트·개인·업무·공유 Markdown Source를 분리 등록하고 SQLite로 색인하여 텍스트·태그·링크·백링크 검색과 증분 스캔을 제공한다.

## 제약 조건

개인과 업무 Source는 기본 민감 상태로 두고 Agent 자동 접근을 금지한다. 원본을 수정·이동·삭제하지 않고 외부 전송, 서버, AI 질의응답, 벡터 검색, 자동 동기화를 구현하지 않는다.

## 기대 결과

동작 가능한 CLI, 사용자 전역 Source Registry와 SQLite DB, 테스트, 설계·결정·품질·릴리스 문서가 저장소에 반영된다.
