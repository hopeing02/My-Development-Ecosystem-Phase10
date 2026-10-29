# DOC-PARSER-1 개발결과

## 결과

**PASS** — 공개 `inspect_document_source()`를 사용하는 개정 명세로 실제 C 드라이브에서 W1을 재실행했다.
개발 전 작성한 예상 기록이 아니라 실제 결과 JSON과 외부 검증을 확인한 뒤 작성한 결과다.

- STEP / TASK: DOC-PARSER-1 / DOC-PARSER-001
- 작성 시각(UTC): 2026-10-25T07:15:19+00:00
- 공개 API·명세·요청 기준 GitHub 커밋: `4f23c9828c531ce4b4c335ed843cd03b1cb88769`
- 명세 원본: [DOC-PARSER-1.md](../steps/DOC-PARSER-1.md)
- 명세 SHA-256: `1987d2d8f415853d6feaf997e078a2768e492746a5124f711ad582aeaf55dbfd`
- 기계용 결과: `.mde/codex-development/DOC-PARSER-1-result.json`
- 결과 JSON SHA-256: `65d94a3e6a6ff881fce8563112996ae789c4203e731a13ae0336e4f6abcd684d`

## 변경 파일

- `apps/document-parser/src/document_parser/hwpx.py`
- `apps/document-parser/tests/test_hwpx.py`

이 결과 MD는 외부 검증 종료 후 추가한 기록이다. Codex의 변경 목록이나 allowedFiles에 포함하지 않았다.

## 기존 코드 재사용

실제 호출 흐름은 다음과 같다.

```text
extract_hwpx_text(file_path)
  → inspect_document_source(file_path)
  → validate_source(Path(file_path).expanduser())
  → DocumentSource
```

HWPX 모듈은 공개 inspect_document_source를 직접 호출하며 validate_source를 직접 호출하지 않는다.
새 공개 함수의 원문 file_path= 호출·홈 경로 확장과 기존 validate_source(path=...) 호출은 함께 유지한다.
공개 API 보완 단계의 결과는 [DOC-PARSER-0-api-result.md](DOC-PARSER-0-api-result.md)에 분리했다.
검증 완료된 validate_source 본문은 API 보완 전 커밋과 AST가 동일하다.

## 신규 함수

- 이 STEP: `extract_hwpx_text(file_path: str | Path) -> str`.
- 필요 이유: 기존 입력 검사는 메타데이터만 다루므로 HWPX의 ZIP/XML 텍스트 추출이 별도로 필요하다.
- 선행 API 보완: `inspect_document_source()`는 검증 알고리즘을 복제하지 않는 공개 호환 함수다.
- source.py·__init__.py·test_source.py·test_public_api.py는 이번 Codex 실행 중 수정하지 않았다.

## 실제 동작

입력 검증 → hwpx 형식 확인 → ZIP 읽기 → Contents/sectionN.xml 선택 → N 숫자 순 정렬 →
namespace prefix와 무관한 t 텍스트 연결 → 구역 사이 줄바꿈 하나 → str 반환.
원본을 수정하거나 디스크에 압축을 풀지 않는다. 한글과 기존 공백을 유지한다.
비-HWPX, 누락 구역, 잘못된 ZIP/XML은 명세의 예외 계약에 따라 보고한다.

## 테스트

| Gate | 실제 결과 |
|---|---|
| pytest | **47 passed**, 0.07초: 기존 입력 24 + 공개 API 3 + HWPX 20 |
| inspect_document_source 실제 호출 검사 | PASS, spy의 assert_called_once_with 확인 |
| Ruff | PASS, exit 0 |
| Black | PASS, exit 0, 6 files unchanged |
| Codex CLI | exit 0 |
| W1 | success=true, error=null |
| 명세·요청·기존 코드·실행기 해시 | 실행 전후 동일 |
| 실행 중 Git HEAD | 변경 없음 |

사용자 원문 함수의 재사용, 여러 run의 한글·중첩 텍스트와 공백, section0/2/10 순서,
정확한 멤버 경로, namespace·빈 구역·홈 경로, 원본 보존, 입력·ZIP/XML 오류를 검사했다.
직접 만든 메모리 ZIP/XML fixture를 사용했으며 기관 문서는 사용하지 않았다.

## 허용 외 변경

**없음** — W1 변경 파일은 위 두 파일, disallowedFiles=[]다.
기존 입력·공개 API 코드, 고정 명세·요청, 실행기의 SHA-256도 별도 대조했다.
개인 전자책 커밋은 이 STEP의 외부 게시 대상에 포함하지 않는다.

## 실행 방법과 환경

```powershell
Set-Location C:\My-Development-Ecosystem-Phase10
uv run python tools/automation/run_codex_single_task.py `
  --request tasks/pending/DOC-PARSER-1.json `
  --result .mde/codex-development/DOC-PARSER-1-result.json
```

실제 검증은 기존 Python 3.12.14 개발 환경에서 수행했다.
uv를 PATH에 추가하고 UV_PROJECT_ENVIRONMENT로 기존 환경을 선택했으며,
UV_NO_SYNC=1, 프로젝트 src와 MDE src의 PYTHONPATH, BLACK_NUM_WORKERS=1을 설정했다.
새 환경의 의존성 설치 검증은 아니다. 원본 JSON의 projectPath는 `.`을 그대로 사용했다.

## 오류 / 미해결

이번 명세의 기능·외부 Gate 오류는 없다. 대용량·악성 압축 파일의 자원 제한이나
실제 한컴 문서 corpus 검증, 문단·서식·표·이미지, HWP/PDF/OCR은 이번 검증 범위가 아니다.
이전 validate_source 직접 호출 명세의 44개 통과 결과는 별도 아카이브에 보존했고,
이 새 PASS로 소급해서 바꾸지 않았다. Codex 실행 중 commit/push/save/배포는 없었다.

## 최종 운영 코드

```python
"""Extract section text from HWPX without modifying or unpacking the source."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_parser import DocumentSource, inspect_document_source


def extract_hwpx_text(file_path: str | Path) -> str:
    """Return numerically ordered section text, preserving its whitespace.

    Source validation errors propagate unchanged. Invalid ZIP or section XML,
    missing sections and supported non-HWPX sources raise ValueError.
    """
    source: DocumentSource = inspect_document_source(file_path)
    if source.format != "hwpx":
        raise ValueError("Expected HWPX document source")

    try:
        with ZipFile(source.path, "r") as archive:
            sections = []
            for member in archive.infolist():
                match = re.fullmatch(r"Contents/section(\d+)\.xml", member.filename)
                if match is not None:
                    sections.append((int(match.group(1)), member))
            sections.sort(key=lambda section: section[0])
            if not sections:
                raise ValueError("HWPX contains no section XML")

            texts = []
            for _, member in sections:
                try:
                    root = ElementTree.fromstring(archive.read(member))
                except ElementTree.ParseError as error:
                    raise ValueError(
                        f"Invalid HWPX section XML: {member.filename}"
                    ) from error
                texts.append(
                    "".join(
                        "".join(element.itertext())
                        for element in root.iter()
                        if element.tag.rsplit("}", 1)[-1] == "t"
                    )
                )
            return "\n".join(texts)
    except BadZipFile as error:
        raise ValueError("Invalid HWPX ZIP") from error
```

## 실제 파일 추가 검증 — 2026-10-25

사용자가 지정한 실제 HWPX 한 파일을 기존 추출 함수로 읽었다.
구역 XML 1개에서 3,476자(한글 음절 2,350개)를 추출했으며 원본의 실행 전후 SHA-256은 동일했다.
원본 문서·추출 텍스트·상세 실행 JSON은 로컬의 ignored `.mde/document-parser-real-tests/`에 보관한다.
이 Git 문서에는 검증 수치만 기록하며 원문이나 추출 내용을 게시하지 않는다.
DOC-PARSER-1의 구역 단위 연결 계약 때문에 결과는 한 줄이며 문단 복원은 다음 STEP의 범위다.
한 파일의 실제 동작 확인을 모든 HWPX 문서에 대한 완전성 검증으로 확대 해석하지 않는다.

## 커밋 전 재검증 — 2026-10-29

- pytest: **47 passed**, 2.07초.
- Ruff: PASS.
- Black: PASS, 6 files unchanged.
- 기존 입력 API·명세·요청 JSON·pyproject.toml은 게시된 main과 동일함을 확인했다.
- 이번 게시 파일은 hwpx.py, test_hwpx.py, 이 결과 MD 세 개뿐이다.
- 별도 전자책 커밋·테스트 원본·추출 텍스트·ignored 실행 자료는 포함하지 않는다.

## 다음 STEP

DOC-PARSER-2 — HWPX 문단 분리. 이번 실행에서는 시작하지 않았다.
후속 W2에서 JSON→MD 자동 생성과 Workflow/task_runner 연결을 다룬다.
이번 MD는 검증 종료 후 증거를 확인해 별도 작성했으며 W1에 자동 보고 기능을 추가한 것은 아니다.
