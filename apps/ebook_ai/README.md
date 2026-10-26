# EBOOK-AI-01 — Markdown 전자책 제작기

사용자가 검증한 원고 목록을 입력 순서대로 조립합니다. AI API나 MDE 엔진에
의존하지 않으며 목차 `toc.md`와 기본판 `basic.md`를 UTF-8로 생성합니다.

저장소 루트의 PowerShell 7에서 실행합니다. Python 3.12+ 및 uv가 필요합니다.

```powershell
uv run --locked python apps/ebook_ai/ebook_builder.py --manifest apps/ebook_ai/examples/manifest.json --output-dir apps/ebook_ai/output/demo
```

`output/`은 Git 제외 대상입니다. 다시 생성할 때만 `--overwrite`를 붙입니다.
기존 파일은 기본적으로 보호하며 원고와 같은 파일은 덮어쓰기 옵션으로도 거부합니다.

JSON 형식은 다음과 같습니다. `path`는 이 JSON 파일이 있는 폴더를 기준으로 합니다.
`title`은 책과 각 장에 모두 필요하며, `chapters` 순서가 출력 순서입니다.

```json
{
  "title": "가상 전자책",
  "chapters": [
    {"title": "시작", "path": "manuscripts/01.md"},
    {"title": "다음 이야기", "path": "manuscripts/02.md"}
  ]
}
```

본문은 BOM 제거·개행 LF 통일 외에는 보존합니다. 장 구분 제목을 추가하므로
원고에 이미 있는 제목도 그대로 남습니다. 목차는 장 단위입니다.
HTML anchor를 지원하는 Markdown 뷰어에서 링크를 확인하세요.
이미지 복사, 상대 링크 재작성, 본문 anchor 충돌·Markdown 문법 검증은 수행하지 않습니다.
입력 원고의 출판 적합성·링크·문법·내용 승인은 사용자의 사전 검토 대상입니다.
파일 쓰기 중 디스크/권한/동시 실행 오류가 발생하면 출력 일부가 남을 수 있습니다.
한 출력 폴더에 여러 제작 작업을 동시에 실행하지 마세요.

자동 검사만 다시 실행하려면 다음 명령을 사용합니다.

```powershell
.\11_AI_Request\EBOOK_AI_STEP01_Run.ps1 -MdeRepoRoot 'C:\My-Development-Ecosystem-Phase10' -ValidateOnly
```

`-ValidateOnly`를 빼면 같은 폴더의 Codex 요청서를 UTF-8 표준입력으로 전달하여
`codex exec --sandbox workspace-write -` 실행 후 외부 검사를 수행합니다.
이 스크립트에는 commit/push 명령이 없으며 요청서도 해당 작업을 금지합니다.
이는 GitHub 권한을 제거하는 보안 장치는 아닙니다.
CLI 실행 방식은 [OpenAI 공식 문서](https://learn.chatgpt.com/docs/non-interactive-mode)를 따릅니다.

자동 검사 통과와 별개로 STEP 최종 상태는 **사용자 실사용 검증 대기**입니다.
가상 원고로 생성한 두 파일을 열어 목차 이동·한글·장 순서·본문을 확인하세요.

상세 계약과 검사 기록: [EBOOK-AI-01](../../docs/15_projects/ebook_ai/implementation/EBOOK-AI-01.md).

## STEP 02 — 승인된 해설로 확장판 생성

같은 명령에 `--supplements`를 지정하면 `expanded.md`를 추가합니다.
기존 원고 목록과 기존 명령의 동작은 그대로 유지합니다.

```powershell
uv run --locked python apps/ebook_ai/ebook_builder.py --manifest apps/ebook_ai/examples/manifest.json --output-dir apps/ebook_ai/output/expanded-demo --supplements apps/ebook_ai/examples/approved-supplements.example.json
```

uv가 PATH에 없으면 위 `uv run --locked python` 대신 저장소의
`.\.venv\Scripts\python.exe`를 사용할 수 있습니다.

보충 목록은 원고 목록과 별개 JSON입니다.

```json
{
  "supplements": [
    {"step": "chapter-001", "path": "supplements/STEP_01_explanation.md"}
  ]
}
```

현재 STEP 01에는 별도 STEP ID 필드가 없습니다. `step`은 **기본판의 실제 장 앵커**를
사용합니다. `chapter-001`은 첫 장, `chapter-002`는 두 번째 장입니다.
첨부 예시의 `STEP-01`은 현재 목록에 존재하는 ID가 아니므로 사용하지 않습니다.
원고 순서를 바꾸면 장 앵커도 달라지므로 보충 목록의 연결 대상을 다시 확인하세요.

`path`는 **기존 원고 목록 JSON이 있는 폴더**를 기준으로 합니다.
보충 JSON의 위치나 현재 작업 폴더를 기준으로 하지 않습니다.
절대경로·상위경로(`..`)·루트 밖 링크·중복 장/파일·없는 장·빈 원고·잘못된 UTF-8을 거부합니다.
장 뒤에 `### 추가 해설`을 붙이고 승인된 보충 본문을 넣습니다. 표·코드·한글은
BOM 제거와 개행 LF 통일 외에는 보존합니다. 해설이 없는 장에는 이 제목을 넣지 않습니다.
예제 보충 원고는 사용자가 제공한 STEP 02 ZIP의 공개 가상 원고를 그대로 사용합니다.

기존 `toc.md`·`basic.md`가 있으면 예상 STEP 01 출력과 바이트를 비교하고
**파일을 다시 쓰지 않습니다**. 내용이 다르면 `--overwrite`를 붙여도 오류로 중단합니다.
두 파일이 없으면 기존 렌더링으로 생성합니다.
확장 모드의 `--overwrite`는 **기존 expanded.md 교체에만** 적용됩니다.
검증 오류 시 세 결과물을 모두 보존합니다. 확장판은 같은 폴더의 임시 파일에
완성한 뒤 게시하며, 기본 저장은 기존 파일을 보호하고 덮어쓰기는 원자적으로 교체합니다.
하드링크를 지원하는 로컬 파일시스템이 필요합니다. 모든 결과 파일을 한꺼번에
보장하는 트랜잭션은 아니므로 첫 생성의 I/O 오류에서는 기본판 일부가 남을 수 있습니다.
입력·출력 폴더를 다른 작업에서 동시에 수정하는 상황은 지원하지 않습니다.

공개 Python API는 `build_ebook(manifest_path, output_dir, *, overwrite=False,
supplements_path=None)`입니다. 반환형 `BuildResult`는 STEP 01 그대로이며
확장판 경로는 `output_dir/expanded.md`입니다.
`--supplements`가 없으면 기존 expanded.md도 생성·수정·삭제하지 않습니다.

검사는 실행 파일 대신 Python 모듈로도 실행할 수 있습니다.

```powershell
uv run --locked python -m pytest apps/ebook_ai/tests -q
uv run --locked python -m ruff check apps/ebook_ai
uv run --locked python -m black --check --workers 1 apps/ebook_ai
git diff --check
```

확장판을 읽고 장별 해설 위치와 기본판 보존을 확인하기 전까지 STEP 02는
**사용자 실사용 검증 대기**입니다. AI 집필·PDF/EPUB·MDE 핵심 변경은 포함하지 않습니다.
상세 설계와 검증 기록: [EBOOK-AI-02](../../docs/15_projects/ebook_ai/implementation/EBOOK-AI-02.md).
