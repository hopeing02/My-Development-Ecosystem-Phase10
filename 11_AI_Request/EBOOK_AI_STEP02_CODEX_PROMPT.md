# EBOOK-AI-02 실제 구현 요청 기록

- 요청 ID: EBOOK-AI-02
- 작성일: 2026-10-26
- 대상 AI: Codex
- 목적: STEP 01 기본판을 유지하고 승인된 해설 원고로 확장판을 추가한다.
- 처리 상태: Review — 구현·자동 검사 후 사용자 실사용 검증 대기.

## 사용자 요청과 첨부 자료의 구분

사용자 요청은 기존 toc.md/basic.md 및 원본 보존, 별도 승인 해설로 expanded.md 생성,
AI 자동 집필 제외다. 제공된 STEP 02 ZIP은 요구사항·예시 자료로 읽고 실행하지 않았다.
이 요청서는 첨부 지시문의 불확실한 파일명/STEP ID를 현재 로컬 계약에 맞춰 기록한 것이다.
자동화 스크립트에서 재사용하려면 이 파일과 해당 실행 스크립트를 같은 폴더에 둔다.
현재 세션은 별도 codex exec 호출 없이 이 요청을 직접 구현하고 외부 검사를 실행했다.

## 요청 내용과 적용 계약

1. 로컬 AGENTS.md, 공통 개발지침 8종의 관련 원칙, 기존 코드·테스트를 확인한다.
2. STEP 01 pytest를 먼저 실행한다. 실패하면 기존 코드를 임의로 수정하지 않는다.
3. 실제 기존 `_read_manifest`, `_title`, `_markdown_text`, `build_ebook`, `BuildResult`를 재사용한다.
4. 기존 입력 manifest는 `title`·`chapters[{title,path}]`이며 그대로 둔다.
5. 보충 JSON은 `supplements[{step,path}]`다. step은 기존 장 앵커 `chapter-001` 형식이다.
   첨부 예시의 STEP-01을 구현에 존재하는 ID로 간주하지 않는다.
6. path는 원고 manifest 폴더 기준 상대경로다. 누락·중복·없는 장·잘못된 JSON/UTF-8·
   절대/상위 경로·링크 외부 이탈·입출력 같은 파일을 거부한다.
7. 기존 CLI에 선택적 --supplements를 추가한다. 기본판의 장별 렌더링을 재사용하고
   확장판에만 해당 장 뒤 ### 추가 해설과 원고를 붙인다.
8. 기존 toc/basic이 있으면 바이트를 비교하고 재저장하지 않는다. 다르면 실패한다.
   확장 모드의 overwrite는 expanded.md에만 적용한다.
9. 모든 입력 검증을 쓰기 전에 마치고 확장판은 임시 파일로 저장 후 게시한다.
10. 본문·표·코드·한글·장 순서를 보존한다. BOM/개행 처리만 기존과 동일하게 적용한다.

## 제약 조건

변경은 apps/ebook_ai 및 관련 프로젝트 문서·이 요청 기록에 한정한다.
기존 미완료 document-parser 파일을 건드리지 않는다.
MDE Core/Task/Workflow/Agent, AGENTS.md, pyproject.toml, uv.lock은 변경하지 않는다.
실제 판매 원고, 내부기관 자료, AI 집필·교정, PDF/EPUB, DB/프레임워크,
자동 commit/push, 외부 업로드와 다른 에이전트로 위임은 이번 범위에서 제외한다.
테스트 원고는 가상 데이터와 첨부 ZIP에 포함된 공개 가상 해설만 사용한다.

## 기대 결과와 검증

STEP 01 사전 통과, 기본판/목차의 사전 SHA-256 일치, 원본·기존 출력 보존,
해당 장에만 해설 삽입, 2회 출력 바이트 일치, 경로 오류 시 결과 보존,
pytest/Ruff/Black/Git 형식 검사와 가능한 MDE 회귀 검사 결과를 기록한다.
기초 테스트는 32개가 통과했다. 최종 결과와 정확한 실행법은
[EBOOK-AI-02](../docs/15_projects/ebook_ai/implementation/EBOOK-AI-02.md)에 기록한다.
사용자 확인 전 STEP 상태를 검증 완료로 올리지 않는다.
