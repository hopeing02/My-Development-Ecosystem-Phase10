# TEST-009 프로젝트 사용법과 개인 Vault 구조 검증

- 상태: Passed
- 작성일: 2026-07-23

## 대상

- 새 프로젝트 생성 시 `usage/GUIDE-001-usage.md` 자동 생성
- AutoKnowledge Lite 프로젝트의 사용법 문서 위치
- 개인 Vault 카테고리 안내 폴더
- 기존 개인 노트 원본 보존

## 사전 조건

- MDE 저장소의 기존 프로젝트 생성 테스트가 실행 가능하다.
- 개인 Vault Source가 `personal`, `sensitive=true`, `agent access=false`로 등록되어 있다.
- 개인 Vault의 기존 Markdown 문서는 18개다.

## 절차

1. 프로젝트 생성 단위 테스트를 실행한다.
2. 프로젝트 표준과 템플릿에 `usage/`가 포함되었는지 확인한다.
3. 개인 Vault에 분류 폴더별 `README.md`가 생성되었는지 확인한다.
4. 변경 전 기존 `AutoKnowledge/` 파일과 변경 후 파일의 SHA-256을 비교한다.
5. 개인 Source를 증분 스캔하고 오류와 문서 수를 확인한다.
6. 기본 검색에서 개인 Source가 계속 제외되는지 확인한다.

## 예상 결과

- 새 프로젝트에 사용법 가이드가 자동 생성된다.
- 기존 프로젝트 사용법이 `docs/15_projects/<project>/usage/`에서 관리된다.
- 개인 Vault 폴더 분류가 추가되지만 기존 노트는 이동·수정되지 않는다.
- 개인 Source의 민감정보 보호 정책이 유지된다.

## 실제 결과

```text
Focused project/scaffold tests: 19 passed
Full regression tests: 144 passed
Existing AutoKnowledge files: 17
SHA-256 mismatches: 0
Category folders added: 6
Knowledge scan: Added 6, Updated 1, Deleted 0, Unchanged 17, Errors 0
Source-limited search: personal result returned
Default search: personal result not returned
ruff check .: failed on local .test-deps packages, 442 errors
ruff check . --exclude .test-deps: passed
ruff format --check for changed Python files: passed
```

결과: Passed
