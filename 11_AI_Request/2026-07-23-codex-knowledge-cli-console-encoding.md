# AI 요청서

- 요청 ID: AIR-2026-07-23-002
- 작성일: 2026-07-23
- 대상 AI: Codex
- 목적: Windows CP949 환경의 Knowledge CLI Unicode 출력 중단 수정
- 처리 상태: Completed

## 요청 내용

Knowledge 검색 결과에 CP949로 표현할 수 없는 문자가 있어도 CLI가 중단되지 않도록 수정하고 실제 CP949 출력과 전체 회귀를 검증한다.

## 제약 조건

- 원본 Markdown과 SQLite 원문을 수정하지 않는다.
- 콘솔의 기존 인코딩을 강제로 UTF-8로 바꾸지 않는다.
- 미지원 문자만 안전하게 대체한다.
- 검색어와 결과 본문을 감사 로그에 기록하지 않는다.
- 테스트·ADR·CODE·QA·DevelopmentLog를 함께 기록한다.

## 기대 결과

- CP949 `UnicodeEncodeError` 재발 방지
- 미지원 문자 대체 출력
- Knowledge CLI와 전체 MDE 테스트 통과
