# TEST-003 Knowledge 안전 감사 로그 검증

- 버전: 1.1.0
- 상태: Passed
- 작성일: 2026-07-22

## 검증 항목

- Source add/update/remove 이벤트 순서
- scan started/completed 이벤트와 Added/Updated/Deleted/Unchanged/Error 건수
- 파일 오류의 상대경로와 안전한 오류 유형
- Source 절대경로 비기록
- 문서 본문 비기록
- 검색어와 검색 결과 비기록
- 검색 실행 전후 감사 로그 불변
- 테스트 격리 경로 사용

## 결과

```text
Knowledge tests: 26 passed
Full regression: 134 passed
Ruff: passed
Formatter: 22 files already formatted
```

## 실제 사용자 환경 검증

`mde-docs`를 연속 두 번 증분 스캔하고 사용자 전역 감사 로그를 검사했다.

```text
Audit file: C:\Users\<user>\.mde\knowledge\logs\knowledge-2026-07-22.log

First incremental scan:
Added: 4
Updated: 8
Deleted: 0
Unchanged: 78
Errors: 0

Second incremental scan:
Added: 0
Updated: 0
Deleted: 0
Unchanged: 90
Errors: 0

Audit events: scan.started, scan.completed, scan.started, scan.completed
Absolute Source path present: false
Search query present: false
```

SQLite의 최근 스캔 이력은 `(0, 0, 0, 90, 0)`, `(4, 8, 0, 78, 0)`, `(86, 0, 0, 0, 0)` 순서로 확인됐다.
