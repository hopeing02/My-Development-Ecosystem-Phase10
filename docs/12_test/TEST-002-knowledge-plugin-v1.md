# TEST-002 Knowledge Plugin v1 검증

- 버전: 1.0.0
- 상태: Passed
- 작성일: 2026-07-22

## 단위·통합 테스트

- Source Category 5종의 보안 기본값
- 한글·공백·상대경로 정규화와 중복 차단
- 민감 Source Agent 접근 확인 플래그
- frontmatter, H1, 태그, aliases, Markdown/외부/위키/첨부 링크
- UTF-8/BOM, 파일 오류 지속, 제외 디렉터리
- SQLite Source 격리, 동일 파일명, FTS5/LIKE, 태그, 백링크
- 기본 민감 Source 제외와 명시적 Source 검색
- Agent 접근 차단
- Added/Updated/Deleted/Unchanged 증분 스캔
- Source 제거 후 원본과 다른 Source 색인 보존
- CLI add/list/show/update/remove/scan/search

## 결과

```text
Knowledge tests: 23 passed
Full regression: 131 passed
Ruff: passed with external temporary directories excluded
Formatter: 20 changed/touched files already formatted
Type check: not run; no mypy configuration or installed mypy module
```

초기 `uv` 명령은 실행 파일이 PATH에 없어 환경 오류가 발생했다. 동일 Python 3.12 환경의 로컬 pytest와 Ruff 모듈로 네트워크 다운로드 없이 검증했다.

## 실제 사용자 환경 스모크 테스트

2026-07-22에 저장소의 `docs`를 `mde-docs` Source로 등록했다.

```text
Source: ks-001 / mde-docs / development / markdown
Sensitive: false
Agent access: true
Scanned: 86
Added: 86
Updated: 0
Deleted: 0
Unchanged: 0
Errors: 0
FTS documents: 86
Search query: workflow
Search limit: 5
Search results: 5
```

Registry와 SQLite는 `C:\Users\<user>\.mde\knowledge`에 생성됐다. 프로젝트 내부 `.mde\knowledge`와 프로젝트 DB는 생성되지 않았으며 Git 작업 트리에 사용자 데이터 파일이 추가되지 않았다.
