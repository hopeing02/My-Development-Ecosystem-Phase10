# EBOOK-AI-01 Codex 개발 요청서

- 요청 ID: EBOOK-AI-01
- 작성일: 2026-10-23
- 대상 AI: Codex
- 처리 상태: Review — 구현·자동 검사 후 사용자 실사용 검증 대기
- 목적: 검증 완료된 Markdown 원고 목록을 목차와 기본판으로 조립한다.

## 역할과 요청 내용

기존 MDE 저장소의 AGENTS.md와 개발표준, 관련 상위 지침을 먼저 읽는다.
로컬에 이미 있는 ebook_ai와 Codex Provider/단일 작업 실행기를 확인한다.
같은 기능이 구현되어 있으면 검토하고 필요한 범위만 보완한다.
설계 반복으로 끝내지 말고 아래 계약을 실행 가능한 Python과 pytest로 구현한다.

## 입력과 출력 계약

- Python 3.12+, UTF-8, 타입 힌트, 표준 logging. 런타임은 표준 라이브러리만 사용한다.
- `apps/ebook_ai/ebook_builder.py`에 `build_ebook(manifest_path, output_dir, *, overwrite=False)`와 CLI를 제공한다.
- JSON manifest: `{"title": "도서명", "chapters": [{"title": "장 제목", "path": "원고.md"}]}`.
- 원고 경로는 manifest 위치 기준. 입력 목록 순서를 유지하고 `.md` 확장자는 대소문자를 구분하지 않는다.
- 모든 원고를 읽어 검증한 뒤 출력 폴더에 `toc.md`, `basic.md`를 쓴다.
- 제목·장 목록·경로 누락, 비어 있는 원고, 읽기 실패, 비 UTF-8, 중복 원고는 오류로 처리한다.
- 같은 장 제목은 허용하고 순번 anchor로 구분한다. TOC는 기본판의 해당 장을 연결한다.
- 본문을 집필·요약·삭제·재구성하지 않는다. BOM 제거와 개행 LF 통일만 허용한다.
- 기본판에는 책 제목·목차·장 구분을 추가한다. 입력 제목/본문의 검증·승인 주체는 사용자다.
- 기존 출력은 기본 거부한다. 명시적 `--overwrite`에서도 입력 원고·manifest를 덮어쓸 수 없다.
- 상대 이미지/링크 재배치와 하위 제목 전체 목차 추출은 이 STEP에 포함하지 않는다.
- CLI: `python apps/ebook_ai/ebook_builder.py --manifest MANIFEST --output-dir OUTPUT [--overwrite]`.
- 실패는 비영 종료와 구체적인 오류 메시지로 알린다. 가짜 성공 처리를 하지 않는다.

## 허용 범위와 제약 조건

변경은 `apps/ebook_ai/`, 이 요청서와 실행 스크립트,
`docs/15_projects/ebook_ai/`의 새 문서로 제한한다.
기존 MDE 핵심, Provider, Agent, Workflow, pyproject.toml, uv.lock, CON/GOV는 변경하지 않는다.
실제 판매 원고·비밀키·개인 자료를 사용하지 않는다. 공개 가능한 가상 원고만 만든다.
AI 원고 생성, 확장판, PDF/EPUB, Task 직접 연결, 자동 수정 반복은 다음 STEP이다.
commit, push, PR, 배포, 릴리스, mde save와 다른 에이전트로 위임을 실행하지 않는다.
외부 명령은 오류 코드를 확인하고 실패 원인을 보고한다.

## 품질 기준과 기대 결과

`apps/ebook_ai/tests/test_ebook_builder.py`에서 순서·한국어·공백 경로·본문 보존,
TOC anchor, 동일 제목, 재현성, 잘못된 입력, 덮어쓰기/원본 보호, CLI를 검증한다.

```powershell
uv run --locked pytest apps/ebook_ai/tests -q
uv run --locked ruff check apps/ebook_ai
uv run --locked black --check --workers 1 apps/ebook_ai
git diff --check
```

설계 계약, 테스트 대상·사전 조건·절차·예상/실제 결과, 재실행 방법을
프로젝트 문서에 기록한다. 실행하지 않은 검사는 통과했다고 쓰지 않는다.
자동 검사가 통과해도 최종 상태는 사용자 실사용 검증 대기다.
생성/수정 파일, 실행 명령, 실제 검사 결과와 남은 제약을 보고한다.
