# EBOOK-AI-02 — 승인된 해설로 확장판 자동 생성

- 문서 번호 / STEP: EBOOK-AI-02
- 버전: 0.1.0
- 상태: Review — 사용자 실사용 검증 대기
- 작성일: 2026-10-26
- 작성자: Codex
- 변경 이력: 기존 기본판 생성기에 선택적 확장판 조립 기능과 회귀 테스트 추가.
- 목적: 기존 toc.md/basic.md와 원본을 보존하며 expanded.md를 추가한다.

## 목표·기준과 기존 구조

사용자 요청과 다운로드 ZIP을 구분했다. ZIP의 스크립트는 실행하지 않고 내용만 읽었다.
첨부 문서의 구현 미확인 상태와 approved-chapters.json/STEP-01 예시는 그대로
가정하지 않고 현재 로컬 구현을 확인했다. 별도 codex exec나 다른 에이전트를 호출하지 않았다.

로컬 AGENTS.md/DEV-001/STD-001 및 docs/development-guidelines의 공통 원칙,
전자책 원칙, 보안, 내부판·인터넷판 분리, 상용화·라이선스, 마라토너식 개발,
오케스트레이션, 코드 생성 지침의 관련 항목을 확인했다.
이번 변경은 오프라인 인터넷판의 가상 원고 조립이며 기관 전용 자산을 사용하지 않는다.
상용 라이선스·AI 오케스트레이션은 추가하지 않는다.

작업 시작 HEAD는 83aac31, 브랜치는 ebook-ai-01이었으며 ebook-ai-02를 새로 만들었다.
기존 document-parser 소스/테스트/결과 문서 세 개가 untracked 상태였고 그대로 보존한다.
기존 STEP 01 tests 두 파일도 수정하지 않는다.

## 기존 재사용 / 신규 함수 / 수정 함수

| 구분 | 실제 대상과 이유 |
| --- | --- |
| 기존 재사용 | `_read_manifest`, `_title`, `_markdown_text`, `BuildResult` 및 `build_ebook`의 장별 텍스트 생성 |
| 신규 함수 | `_read_supplements`: 기존 로더와 형식·경로 경계가 다른 승인 해설 목록 검증에 필요 |
| 수정 함수 | `build_ebook`: 선택 인자, 검증 선행, 기존 파일 보존, 같은 렌더링 조각으로 확장판 생성·저장 |
| 수정 함수 | `main`: 기존 CLI에 --supplements를 추가하고 선택 실행 결과를 표시 |

새 클래스, 중복 Markdown 파서, 별도 CLI, 의존성을 추가하지 않았다.
원고 목록에 STEP ID가 없어 기존 앵커 chapter-001을 보충 연결 키로 사용한다.
기존 manifest를 변환하거나 STEP-01을 자동 별칭으로 만들지 않는다.
정확한 데이터/API/보존 계약: [SDS-002](../SDS/SDS-002-expanded-edition.md).

## 파일별 변경

- apps/ebook_ai/ebook_builder.py: 확장판 기능을 선택적으로 추가. 기본 명령·반환형 유지.
- apps/ebook_ai/tests/test_expanded_edition.py: 기존 32개 테스트와 별개로 확장 기능 검증.
- apps/ebook_ai/examples/approved-supplements.example.json: 첫 장에만 승인 해설 연결.
- apps/ebook_ai/examples/supplements/STEP_01_explanation.md: 사용자 ZIP의 가상 해설 원문 그대로.
- apps/ebook_ai/README.md: 정확한 API/CLI·ID·보존/오류 계약 추가.
- 11_AI_Request/EBOOK_AI_STEP02_CODEX_PROMPT.md: 실제 요청과 로컬 계약 기록.
- 프로젝트 SDS-002 및 이 기록: 설계·실행·검증 결과.

원본 테스트, STEP 01 manifest/가상 원고, pyproject/lock, MDE 코어·Provider·Workflow·Agent는 변경하지 않는다.
기존 파일 수정분의 전체 내용은 실제 파일과 검토용 ZIP에 포함한다.

## 실행

저장소 루트에서 Python 3.12+와 pytest/Ruff/Black이 설치된 환경을 사용한다.

```powershell
Set-Location 'C:\My-Development-Ecosystem-Phase10'
.\.venv\Scripts\python.exe apps/ebook_ai/ebook_builder.py --manifest apps/ebook_ai/examples/manifest.json --output-dir apps/ebook_ai/output/expanded-demo --supplements apps/ebook_ai/examples/approved-supplements.example.json
```

이 명령은 이전 기본판이 같은 폴더에 있어도 일치 여부를 확인하고 그대로 보존한다.
확장판 재생성 때만 --overwrite를 추가한다. 기존 기본판과 다르면 덮어쓰기 대신 실패한다.
원고 목록의 첫 장이 chapter-001이며 승인 JSON의 상대경로 기준은 원고 목록 폴더다.
기존 toc.md는 basic.md를 가리키고 확장판 안에는 같은 내부 목차/장 앵커가 있다.

## 검증 대상·사전 조건·절차·예상 결과

사전 조건: Python 3.12.14, 기존 lock의 pytest 9.1.1/Ruff 0.15.20/Black 26.10.1,
uv 0.13.5. uv는 이 대화 작업 폴더의 기존 가상환경 실행 파일을 사용한다.
설치/잠금 파일을 바꾸지 않도록 uv run --locked로 실행하며 Black은 Python 모듈을 사용한다.

```powershell
uv run --locked python -m pytest apps/ebook_ai/tests -q
uv run --locked python -m ruff check apps/ebook_ai
uv run --locked python -m black --check --workers 1 apps/ebook_ai
uv run --locked python -m pytest -q
git diff --check
```

| 대상 | 절차와 예상 결과 |
| --- | --- |
| STEP 01 사전 게이트 | 기능 변경 전 기존 테스트 32개 통과 |
| 기본판 호환성 | 수정 전 예제 결과 SHA를 고정한 테스트로 toc/basic 바이트 일치 |
| 기존 출력 보존 | 파일 바이트·mtime·inode 보존, 사용자 편집본이면 오류 |
| 확장판 | 첫 장 뒤에만 해설, 둘째 장에 미생성, 표/코드/한글/앵커 보존 |
| 입력 오류 | 누락·중복·없는 장·JSON/인코딩·절대/상위/UNC/ADS·링크 이탈 거부 |
| 출력 오류 | 입력/다른 출력과 같은 파일 거부, 교체 실패·경쟁 생성 시 원래 파일 보존 및 임시 파일 정리 |
| 재현성 | 서로 다른 폴더와 같은 폴더 재생성에서 동일 바이트 |
| 범위 | 외부 API·AI 집필·자동 commit/push 없음, 다른 작업 파일 해시 불변 |

## 실제 결과

기능 변경 전 pytest: **32 passed**, 2.57초.

| 최종 검사 | 실제 결과 |
| --- | --- |
| 전자책 전체 pytest | **73 passed**, 3.36초 (기존 32 + 신규 41) |
| MDE 루트 회귀 | **320 passed, 1 skipped**, 52.62초 |
| Ruff | All checks passed, exit 0 |
| Black | 5 files unchanged, exit 0 |
| git diff --check | 통과 |

루트 기본 testpaths에는 전자책 앱이 포함되지 않으므로 앱 테스트는 별도로 실행했다.
전자책 symlink/junction 이탈 검사 둘 다 실제 파일시스템으로 실행되어 통과했다.
MDE 루트의 skip은 기존 테스트의 운영체제 조건이며 전자책 검사는 skip이 없다.

CLI 가상 예제 결과는 apps/ebook_ai/output/step02-demo-20261026에 생성했다.
수정 전 코드로 생성한 기본판/목차를 넣어둔 뒤 새 CLI를 실행했으며,
두 파일의 바이트와 mtime가 유지되고 확장판만 추가되었다.
ZIP의 해설 바이트는 그대로이고 첫 장 뒤에만 추가되며 2회 생성 결과도 동일하다.
검증 JSON은 같은 폴더의 test-result.json에 기록했다. 이 폴더는 Git에서 제외된다.

기본판 SHA-256: 0d20f0884af089f4f0d4a31512eb2ac92aab08b6fb1bd2d791976eedaf1be3e2.
목차 SHA-256: 8b5bcc4c4d75d2f8a2d0be1b8328131e88f8eb237a9ad94fcd796d9f698e9002.
두 값은 기능 변경 전 코드로 생성한 결과와 동일하다.

## 실제 확인과 상태

basic.md와 expanded.md를 열어 첫 장 뒤의 추가 해설, 표·코드 블록,
둘째 장 순서·본문, 목차 이동을 확인한다.
이 자동 검사 결과를 사용자 실사용 승인으로 간주하지 않는다. 상태는 검증 대기다.
AI 교정 제안·집필, PDF/EPUB, 확장된 원고 편집은 다음 STEP이며 이번에는 시작하지 않는다.

## 자체 검토 / Git 명령

기존 함수 재사용, 기본판 바이트 보존, 승인 목록만 사용, 경로와 쓰기 오류,
추가 의존성 없는 최소 변경, 원본 및 다른 작업 보존을 확인한다.
자동 commit/push는 실행하지 않는다. 필요하면 사용자 검토 후 아래 명령을 사용한다.

```powershell
git add -- apps/ebook_ai/ebook_builder.py apps/ebook_ai/README.md apps/ebook_ai/tests/test_expanded_edition.py apps/ebook_ai/examples/approved-supplements.example.json apps/ebook_ai/examples/supplements/STEP_01_explanation.md 11_AI_Request/EBOOK_AI_STEP02_CODEX_PROMPT.md docs/15_projects/ebook_ai/SDS/SDS-002-expanded-edition.md docs/15_projects/ebook_ai/implementation/EBOOK-AI-02.md
git commit -m "feat(ebook-ai): assemble approved expanded editions"
```
