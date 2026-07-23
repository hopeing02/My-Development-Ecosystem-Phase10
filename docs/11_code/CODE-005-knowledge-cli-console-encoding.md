# CODE-005 Knowledge CLI Unicode 출력 보호 구현

- 상태: Implemented
- 작성일: 2026-07-23

## 대상

- `packages/mde-core/src/mde/knowledge/cli.py`
- `packages/mde-core/tests/knowledge/test_cli.py`

## 구현

`run()`이 Source 접근이나 출력 전에 `_configure_console_output()`을 호출한다. stdout이 `reconfigure`를 지원하면 현재 encoding을 유지한 채 오류 처리만 `replace`로 바꾼다.

이 정책은 출력할 수 없는 문자에서 예외를 발생시키는 대신 해당 문자만 `?`로 표시한다. 문서 내용과 검색 결과 데이터는 변경하지 않는다.

## 영향 범위

Knowledge CLI의 add, list, show, update, remove, scan, search, backlinks 출력에 적용된다. 다른 MDE 명령의 stdout 정책은 변경하지 않는다.
