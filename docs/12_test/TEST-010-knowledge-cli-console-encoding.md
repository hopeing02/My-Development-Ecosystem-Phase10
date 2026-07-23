# TEST-010 Knowledge CLI CP949 출력 회귀 검증

- 상태: Passed
- 작성일: 2026-07-23

## 대상

- CP949 strict stdout에서 미지원 Unicode 문자 출력
- Knowledge 검색 결과의 제목과 문맥 출력
- 기존 Knowledge CLI 회귀
- 전체 MDE 회귀

## 사전 조건

- 검색 결과 제목과 문맥에 em dash `—`가 포함된다.
- stdout은 `encoding="cp949"`, `errors="strict"`로 시작한다.

## 절차

1. CP949 TextIOWrapper에 Knowledge 검색 결과를 출력한다.
2. 명령 종료 코드와 실제 출력 문자열을 확인한다.
3. Knowledge CLI 테스트를 실행한다.
4. 실제 CLI를 `PYTHONIOENCODING=cp949:strict`로 실행한다.
5. 전체 pytest, Ruff, formatter 검사를 실행한다.

## 예상 결과

- `UnicodeEncodeError`가 발생하지 않는다.
- 종료 코드는 0이다.
- 한글은 유지되고 em dash만 `?`로 대체된다.
- 기존 기능과 보안 정책의 회귀가 없다.

## 실제 결과

```text
Knowledge CLI focused tests: passed
CP949 unsupported em dash output: replaced with ?
UTF-8 em dash output: preserved
Actual PYTHONIOENCODING=cp949:strict CLI: exit code 0
Full regression tests: 146 passed
ruff check . --exclude .test-deps: passed
ruff format --check changed Python files: passed
Original Markdown modified: no
SQLite indexed content modified: no
```

결과: Passed
