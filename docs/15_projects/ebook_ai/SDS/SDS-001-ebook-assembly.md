# SDS-001 — 전자책 Markdown 조립 계약

- 문서 번호: ebook_ai/SDS-001
- 버전: 0.1.0
- 상태: Review
- 작성일: 2026-10-23
- 작성자: Codex
- 변경 이력: EBOOK-AI-01 최소 설계 계약 최초 작성.
- 목적: 검증된 원고의 순서와 내용을 보존하는 오프라인 조립 기능을 정의한다.

## 요구사항과 구조

JSON 목록 → 입력 검증 → 원고 전체 읽기 → 목차/기본판 문자열 생성 → 파일 저장.
독립 앱 모듈 하나가 책임지며 MDE 핵심이나 AI Provider를 호출하지 않는다.
기존 Codex CLI Provider/W1 기능은 후속 Task 연동의 재사용 후보이며 이번에는 수정하지 않는다.

## 데이터와 API

manifest는 `title: str`, `chapters: list[{title: str, path: str}]`다.
책과 장 제목은 비어 있지 않은 출력 가능한 한 줄 문자열이다.
`path`는 로컬 `.md` 파일이며 상대 경로는 manifest 폴더 기준이다.
목록과 원고는 UTF-8/UTF-8 BOM을 지원한다. 원고가 비어 있거나 중복이면 거부한다.
장 제목이 같아도 목록 위치로 부여한 `chapter-001` 형식의 anchor는 서로 다르다.

`build_ebook(manifest_path, output_dir, *, overwrite=False)`는
불변 `BuildResult(toc_path, basic_path, chapter_count)`를 반환한다.
검증 오류는 `EbookBuildError`, 파일 저장 오류는 원래 `OSError`로 전달한다.
CLI는 입력·파일시스템 오류를 stderr와 exit 1로 보고하며 성공은 exit 0이다.
잘못된 CLI 인수는 argparse 표준 exit 2다.
UI와 서버 API, DB는 추가하지 않는다. 사용자 접점은 CLI와 Markdown 뷰어다.

## 출력과 보존

`toc.md`는 `basic.md#chapter-NNN`에 연결된다. 기본판에는 책 제목, 내부 목차,
장 anchor/제목, 원고 본문이 들어간다. 제목 메타데이터는 Markdown/HTML을 escape한다.
원고 본문은 BOM 제거 및 개행 LF 통일 외에는 보존한다. 기존 제목도 보존한다.
모든 입력 검증이 끝나기 전에는 출력 폴더를 만들지 않는다.
기존 출력은 기본 거부하며 `overwrite=True`에서도 원고/manifest와 같은 파일,
하드링크 및 출력 심볼릭 링크를 거부한다.
두 출력 파일의 저장은 하나의 트랜잭션이 아니므로 I/O 실패 시 부분 출력이 남을 수 있다.
검증 후 파일이 외부에서 바뀌는 동시 수정 상황은 보호 범위 밖이다.

## 범위와 자체 검토

공개 가능한 가상 원고만 예제로 사용한다. 원고 검증/승인을 자동 판정하지 않는다.
이미지·상대 링크 재배치, Markdown 문법 검사, 하위 제목 목차, AI 집필, 확장판,
PDF/EPUB, MDE Task 연동은 다음 STEP이다.
원고 내 `chapter-NNN` 사용자 anchor와의 충돌도 사전 검토 대상이다.
API와 CLI 계약, 원본 보호, 오류, 테스트 가능성 및 후속 기능 경계를 명시했다.
관련 기록: [EBOOK-AI-01](../implementation/EBOOK-AI-01.md).
