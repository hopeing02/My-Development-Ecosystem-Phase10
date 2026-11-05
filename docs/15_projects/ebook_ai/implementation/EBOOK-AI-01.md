# EBOOK-AI-01 — MDE + Codex 전자책 제작기 첫 구현

- 문서 번호 / STEP: EBOOK-AI-01
- 버전: 0.1.0
- 상태: Review — 사용자 실사용 검증 대기
- 작성일: 2026-10-23
- 작성자: Codex
- 변경 이력: 독립 Markdown 조립 앱, 가상 원고, pytest, 자동 실행 요청서/스크립트 추가.
- 목적: 기존 MDE 핵심 변경 없이 목차·기본판 생성 기능을 구현하고 자동 검사한다.

## 기준 확인과 재사용 검토

사용자가 지정한 C 드라이브 Phase10 경로는 실제로
`C:\My-Development-Ecosystem-Phase10`이다. 작업 시작 시 `main`은 clean이었으며
로컬 `ebook-ai-01` 브랜치에서 작업했다. `-main` 복사본은 작업 대상으로 사용하지 않았다.

로컬 AGENTS.md, DEV-001, CON-005/010, GOV-006, STD-001, TEST-001과 기존
DOC-PARSER-0 및 TEST-021 기록을 확인했다. 별도로 전달됐다는 공통 지침 8개의
원본 첨부 파일은 이 세션에 없으므로 해당 8개 전체 검토 완료로 표시하지 않는다.
DEV-001의 초기 AutoKnowledge 구현 지시보다 이번 사용자의 전자책 STEP 범위를 우선한다.

로컬에는 CODE-014/015와 TEST-020/021의 Codex CLI Provider 및 W1 단일 작업
연동 기록이 이미 있다. 이전 설명의 “Codex CLI 직접 연동이 확인되지 않음”은
이 로컬 코드 범위에는 적용하지 않는다. 이 STEP은 해당 기능과 MDE 핵심을 수정하지 않는다.
pyproject.toml 및 uv.lock은 기존 내용을 유지하며 런타임 의존성을 추가하지 않는다.

## 생성 파일과 설계

- `apps/ebook_ai/ebook_builder.py`, `__init__.py`: 오프라인 JSON 목록 → Markdown 조립.
- `apps/ebook_ai/tests/test_ebook_builder.py`: 입력·출력·보존·CLI 계약 검증.
- `apps/ebook_ai/tests/test_step_runner.py`: 실제 AI 호출 없이 스크립트 실패 중단 검증.
- `apps/ebook_ai/examples/`: 가상 원고 두 개와 목록. 실제 판매 원고 사용 안 함.
- `apps/ebook_ai/README.md`, `.gitignore`: 사용법과 로컬 결과 Git 제외.
- `11_AI_Request/EBOOK_AI_STEP01_CODEX_PROMPT.md`: 개발 지시문 및 작업 상태.
- `11_AI_Request/EBOOK_AI_STEP01_Run.ps1`: Codex 실행 후 외부 검사, 또는 ValidateOnly.
- 프로젝트 SDS와 이 문서: 최소 설계 계약, 테스트 및 실사용 확인 절차.

설계/API/데이터/CLI와 보존 한계는 [SDS-001](../SDS/SDS-001-ebook-assembly.md)에 명시한다.
구현은 이 Codex 대화에서 직접 수행했다. 별도 `codex exec` 개발 실행을 수행한 것으로
기록하지 않는다. 스크립트의 개발 모드와 외부 검사 전용 모드는 구분한다.

## 테스트 대상·사전 조건·절차·예상 결과

사전 조건: 실행 가능한 PowerShell 7, Git, Python 3.12+, uv,
저장소 dev 의존성 pytest/Ruff/Black. 개발 모드는 로그인된 Codex CLI도 필요하다.

```powershell
Set-Location 'C:\My-Development-Ecosystem-Phase10'
.\11_AI_Request\EBOOK_AI_STEP01_Run.ps1 -MdeRepoRoot (Get-Location).Path -ValidateOnly
uv run --locked python apps/ebook_ai/ebook_builder.py --manifest apps/ebook_ai/examples/manifest.json --output-dir apps/ebook_ai/output/demo
```

`uv`가 PATH에 없다면 설치 후 PATH에 추가하거나 실행 파일의 전체 경로를 사용한다.
개발 모드 실행은 `-ValidateOnly`를 제거한다. 새 작업은 별도 브랜치에서 실행한다.
스크립트와 프롬프트를 같은 폴더에 유지한다. 요청서는 UTF-8 stdin으로 전달하며
명령행 길이와 PowerShell의 한글 인코딩 문제를 줄인다.
CLI 방식 근거: [OpenAI 공식 문서](https://learn.chatgpt.com/docs/non-interactive-mode).

| 검사 | 예상 결과 |
| --- | --- |
| pytest | 목록 순서, 한국어/공백 경로, 본문 보존, BOM/개행, anchor, 동일 제목, 재현성, 잘못된 입력, 원본/기존 결과 보호, CLI 통과 |
| Ruff / Black | 앱 검사 통과 |
| PowerShell | 구문 분석과 ValidateOnly 실제 실행 성공 |
| Git | diff 형식 검사 및 신규 파일 whitespace 검사 통과, 기존 파일 변경 없음 |
| 가상 원고 실행 | output/demo/toc.md와 basic.md 생성 |

## 실제 검사 결과

검증 환경은 CPython 3.12.14, uv 0.13.5, pytest 9.1.1, Ruff 0.15.20,
Black 26.10.1이다. uv를 이 대화 작업 폴더의 전용 가상환경에 설치하고 해당
Scripts 경로를 검사 프로세스 PATH에만 추가했다. 저장소에서
`uv sync --locked --python <Python 3.12.14 경로>`가 성공하여 기존 lock 기준
새 `.venv`를 구성했다. 기존 pyproject/lock의 수정은 없다.

- 전자책·실행기 pytest: **32 passed**, 2.60초. 조립 계약 27개와 실행기 계약 5개다.
- 기존 MDE 루트 회귀 `python -m pytest -q`: **318 passed, 1 skipped**, 50.38초.
  루트 기본 testpaths는 새 앱을 포함하지 않으므로 앱은 명시적 경로로 별도 검사했다.
- 기존 `mde docs check`와 `mde docs check --target knowledge-guide`: 각각 통과.
- 가상 원고 CLI: exit 0, 두 장의 `output/demo/toc.md`, `basic.md` 실제 생성.
  텍스트로 한글·장 순서·표·코드 블록·목차 대상 anchor를 확인했다.
- PowerShell 개발 모드: 실제 Codex 대신 명령 대역으로 정상 진행과
  Codex/pytest/Ruff/Black 각각의 실패 시 후속 단계 중단, 요청서 전체 한글 보존을 검사했다.
  별도 실제 `codex exec` 모델 호출은 하지 않았다.
- Windows PowerShell 5.1은 PC 실행 정책으로 `.ps1` 실행이 거부되었다.
  실행 정책은 변경하지 않았다. 실제 스크립트 실행 검증은 PowerShell 7 기준이다.

| 최종 검사 | 결과 |
| --- | --- |
| 전자책/실행기 pytest | 32 passed, exit 0 |
| Ruff / Black | All checks passed / 4 files unchanged, 각각 exit 0 |
| PowerShell 7 ValidateOnly / Git | 실제 스크립트 성공, tracked diff/new file whitespace 검사 통과 |

새 구현 파일의 전체 내용은 저장소 파일 및 검토 ZIP에 포함한다.
기존 소스 파일을 수정하지 않았으며 사용자 실사용 승인은 아직 대기다.

## 사용자 실사용 검증과 다음 STEP

`toc.md`, `basic.md`를 Markdown 뷰어로 열고 목차 이동, 장 순서, 한글,
표·코드 블록과 원본 본문을 확인한다. 자동 검사가 통과해도 사용자 확인 전에는
STEP 검증 완료·릴리스 완료로 바꾸지 않는다.
다음 구현 대상은 EBOOK-AI-02 기존 자료 기반 확장판 조립이며 이번에는 시작하지 않는다.

## Git 명령과 자체 검토

자동 commit/push는 실행하지 않는다. 사용자 검토 후 필요할 때만 아래 명령을 실행한다.

```powershell
git add -- apps/ebook_ai 11_AI_Request/EBOOK_AI_STEP01_CODEX_PROMPT.md 11_AI_Request/EBOOK_AI_STEP01_Run.ps1 docs/15_projects/ebook_ai
git commit -m "feat(ebook-ai): assemble Markdown table of contents and basic edition"
```

독립 앱, 원고 보존, 테스트와 문서 동기화, 가상 자료만 사용, 후속 범위 분리,
자동 검사/사용자 승인 구분을 확인했다. Push 명령과 제품 핵심/실판매 원고는 포함하지 않는다.
