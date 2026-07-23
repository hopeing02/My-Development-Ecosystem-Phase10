# QA-004 Knowledge CLI Windows 콘솔 출력 품질 기준

- 상태: Passed
- 작성일: 2026-07-23

## 품질 기준

- CP949 stdout에서 지원되는 한글은 그대로 출력한다.
- em dash 등 CP949 미지원 문자 때문에 `knowledge search`가 실패하지 않는다.
- 미지원 문자만 대체하고 제목·경로·검색 문맥의 나머지 내용은 유지한다.
- UTF-8 stdout에서는 원래 Unicode 문자를 그대로 출력한다.
- 원본 Markdown과 SQLite 색인을 수정하지 않는다.
- 기존 Knowledge 보안 필터와 감사 로그 정책에 영향을 주지 않는다.

## 검증

`TEST-010-knowledge-cli-console-encoding.md`의 단위·통합·회귀 결과로 판정한다.

## 결과

CP949와 UTF-8 출력 회귀, 실제 CP949 strict CLI, 전체 146개 테스트, Ruff와 formatter 검사가 통과했다.
