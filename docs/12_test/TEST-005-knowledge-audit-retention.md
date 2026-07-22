# TEST-005 Knowledge 감사 로그 30일 보존 검증

- 버전: 1.2.0
- 상태: Passed
- 작성일: 2026-07-22

## 검증 항목

- 30일 보존 경계 로그 삭제
- 29일 이내 로그 유지
- 다른 이름의 로그 유지
- 잘못된 날짜 파일 유지
- 심볼릭 링크 제외 분기
- 원본 Markdown 유지
- 당일 감사 로그 정상 생성
- 0일 이하 설정 차단

## 결과

```text
Knowledge tests: 29 passed
Full regression: 137 passed
Ruff: passed
Formatter: passed
```

## 실제 사용자 환경 검증

```text
Audit file before: knowledge-2026-07-22.log / retained

Policy apply and index update:
Added: 4
Updated: 6
Deleted: 0
Unchanged: 85
Errors: 0

Immediate rescan:
Added: 0
Updated: 0
Deleted: 0
Unchanged: 95
Errors: 0

Audit file after: knowledge-2026-07-22.log / retained
```

실제 디렉터리에는 만료 로그가 없었으므로 삭제된 사용자 로그는 없다. 30일 경계 삭제는 격리된 임시 디렉터리 단위 테스트로 검증했다.
