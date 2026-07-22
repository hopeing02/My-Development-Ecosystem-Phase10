# TEST-004 uv 실행 환경 복구 검증

- 버전: 1.0.0
- 상태: Passed
- 작성일: 2026-07-22

## 대상

MDE 공식 개발 명령에 필요한 uv 설치, 사용자 PATH 등록과 `uv run mde` 실행을 검증한다.

## 설치 결과

```text
uv version: 0.11.30
install path: C:\Users\<user>\.local\bin\uv.exe
user PATH entry: C:\Users\<user>\.local\bin
installer scope: user local
```

## 실행 결과

```text
Command: uv run mde knowledge scan mde-docs

First run after recovery:
Added: 0
Updated: 2
Deleted: 0
Unchanged: 88
Errors: 0

Second run:
Added: 0
Updated: 0
Deleted: 0
Unchanged: 90
Errors: 0
```

공식 Astral Windows standalone installer를 사용했으며 시스템 전역이 아닌 사용자 로컬 범위에 설치했다.

## 공식 개발 명령 검증

```text
uv run pytest -p no:cacheprovider -q
134 passed

uv run ruff check . [외부 임시 디렉터리 제외]
All checks passed!

uv run ruff format --check [변경 대상]
22 files already formatted

uv run mde knowledge scan mde-docs
Added: 0
Updated: 0
Deleted: 0
Unchanged: 91
Errors: 0
```
