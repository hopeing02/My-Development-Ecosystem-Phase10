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
