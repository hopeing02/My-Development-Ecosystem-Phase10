# CODE-002 Knowledge 안전 감사 로그 구현

- 버전: 1.1.0
- 상태: Implemented
- 작성일: 2026-07-22

## 구현

`mde.knowledge.audit.KnowledgeAuditLogger`가 사용자 전역 일별 `.log` 파일에 JSON 객체를 한 줄씩 추가한다. `KnowledgeService`의 Source 등록·변경·해제와 스캔 시작·완료·실패 이벤트에 연결했다.

## 보안 필드

허용: 시각, 이벤트, Source ID·이름·Category·민감 여부, 변경된 boolean 설정, 스캔 건수, 오류 상대경로와 오류 유형.

금지: Source 절대경로, 문서 본문, 검색어, 검색 결과, 파일 원문, traceback.

검색 실행은 감사 로그 파일을 변경하지 않는다.
