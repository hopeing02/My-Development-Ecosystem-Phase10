# DOC-PARSER-OT1-FIX1 — 중첩 문단 비중복 추출 보완

- 상태: **FIX1 코드 구현·합성/회귀 검증 완료, 실제 문서 운영 재검증 대기** (main 반영/배포 완료가 아님)
- 기준: `main` 4d8e4308bcf4ab7fbf994928708527bcdcda09ce (확인 시점의 기준, 실행 직전 재확인)
- 원인: OT1-001 실문서에서 문단 147개, 기존 문단 합계 7,400자, 각 `t` 1회 집계 3,476자, 반복 집계 3,924자
- 목표: 중첩 `p` 때문에 동일한 `t` 노드가 여러 문단에 중복 산입되지 않도록 수정
- 범위: 원래 `DOC-PARSER-2.md` 역사적 확정 명세는 **수정하지 않음**. 이 파일이 FIX1의 새 변경 계약

## 1. 목적·현재 상태

현재 `extract_hwpx_paragraphs()`는 모든 `p`에 대해 `paragraph.iter()`를 사용하므로, 하위 `p`의 `t`를 바깥 `p`에 다시 포함한다. 코드가 과거 확정 명세를 그대로 따른 결과이므로 기존 명세·결과를 뒤집어 쓰지 않는다.

**변경 계약:** 각 `t` XML 노드는 XML 계층에서 가장 가까운 상위 `p` 하나에만 귀속한다. `p`가 없으면 문단 목록에서 제외한다. 단순히 동일 문자열을 제거하지 않는다. XML 요소 기준 문단 개수와 문단 요소의 전위 순서(preorder)를 유지한다.

문단 요소 사이에 자식 `p`가 끼어 있는 경우, 외부 문단의 앞뒤 텍스트는 같은 외부 문단 문자열로 묶인다. 따라서 **문단 배열 전체를 이어 붙인 문자열의 순서가 원시 XML 텍스트 순서와 반드시 일치하지는 않는다.** 이 STEP은 시각적 읽기 순서·표/글상자 구조 복원을 다루지 않는다.

## 2. 변경·재사용 파일

| 파일 | 처리 |
|---|---|
| `apps/document-parser/src/document_parser/paragraphs.py` | 기존 함수 내부 XML 텍스트 소유권 로직만 최소 수정 |
| `apps/document-parser/tests/test_paragraphs_nested.py` | 중첩·표·동일 텍스트·빈 문단·불변성 합성 회귀 테스트 신규 |
| `docs/15_projects/document-parser/steps/DOC-PARSER-OT1-FIX1.md` | 신규 STEP 보완 명세 |
| `docs/15_projects/document-parser/results/DOC-PARSER-OT1-FIX1-result.md` | **외부 운영 검증 후에만** 작성 |

- **기존 함수 재사용:** `inspect_document_source()`, 기존 `extract_hwpx_paragraphs()`의 ZIP/XML 열기·구역 번호 정렬·예외 계약.
- **수정 함수:** `extract_hwpx_paragraphs()` 하나.
- **신규 운영 함수:** 없음. 추가 모듈·외부 라이브러리·프레임워크 없음.
- **기존 코드 보호:** `source.py`, `hwpx.py`, `__init__.py`, 기존 99개 회귀 테스트, MDE Core, TaskStore, G2, W1, 확정 `DOC-PARSER-2.md` 수정 금지.

## 3. 운영 수정 코드 — `apps/document-parser/src/document_parser/paragraphs.py` (전체)

```python
"""Extract HWPX paragraphs without modifying or unpacking the source."""

import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from document_parser import inspect_document_source


def extract_hwpx_paragraphs(file_path: str | Path) -> list[str]:
    """Return paragraphs with each text node owned by its nearest paragraph.

    Keep document-order paragraph elements and original text whitespace. Nested
    paragraphs do not donate their text to any enclosing paragraph.
    """
    source = inspect_document_source(file_path)
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

            paragraphs: list[str] = []
            for _, member in sections:
                try:
                    root = ElementTree.fromstring(archive.read(member))
                except ElementTree.ParseError as error:
                    raise ValueError(
                        f"Invalid HWPX section XML: {member.filename}"
                    ) from error

                parts: list[list[str]] = []
                stack: list[tuple[ElementTree.Element, int | None]] = [(root, None)]
                while stack:
                    element, owner = stack.pop()
                    name = element.tag.rsplit("}", 1)[-1]
                    if name == "p":
                        owner = len(parts)
                        parts.append([])
                    if name == "t":
                        if owner is not None:
                            parts[owner].append("".join(element.itertext()))
                        continue
                    stack.extend((child, owner) for child in reversed(element))
                paragraphs.extend("".join(content) for content in parts)
            return paragraphs
    except BadZipFile as error:
        raise ValueError("Invalid HWPX ZIP") from error
```

**변경 근거:** `ElementTree`의 전위 탐색을 명시적 스택으로 수행하고, 현재 가장 가까운 `p` 인덱스를 각 자식에 전달한다. `t`를 만나면 현재 소유 문단에 `itertext()` 문자열을 단 한 번 추가하고 해당 `t`의 하위 요소를 재방문하지 않는다. 이 코드는 정상적인 `t` 텍스트 컨테이너 구조를 가정하며, `t` 안에 다시 `p`가 있는 비정상/미검증 구조는 이 STEP의 지원 계약에 포함하지 않는다.

## 4. 신규 테스트 — `apps/document-parser/tests/test_paragraphs_nested.py` (전체)

```python
"""Regression cases for assigning each HWPX text node to one paragraph."""

import hashlib
from collections.abc import Callable
from pathlib import Path
from zipfile import ZipFile

import pytest

from document_parser.paragraphs import extract_hwpx_paragraphs

SourceFactory = Callable[[list[tuple[int, str]]], Path]


@pytest.fixture
def make_hwpx(tmp_path: Path) -> SourceFactory:
    """Write a synthetic HWPX into a temporary directory, never a real document."""

    def create(sections: list[tuple[int, str]]) -> Path:
        path = tmp_path / "synthetic.hwpx"
        with ZipFile(path, "w") as archive:
            for number, xml in sections:
                archive.writestr(f"Contents/section{number}.xml", xml)
        return path

    return create


def test_nested_three_levels_without_duplicate_text(make_hwpx: SourceFactory) -> None:
    path = make_hwpx(
        [
            (
                0,
                "<sec><p><t>외부앞</t><box><p><t>내부앞</t>"
                "<box><p><t>깊은</t></p></box><t>내부뒤</t></p>"
                "</box><t>외부뒤</t></p></sec>",
            )
        ]
    )
    before = hashlib.sha256(path.read_bytes()).hexdigest()

    result = extract_hwpx_paragraphs(path)

    assert result == ["외부앞외부뒤", "내부앞내부뒤", "깊은"]
    assert sum(map(len, result)) == len("외부앞내부앞깊은내부뒤외부뒤")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_table_cell_paragraphs_do_not_repeat_parent_text(
    make_hwpx: SourceFactory,
) -> None:
    path = make_hwpx(
        [
            (
                0,
                '<s:sec xmlns:s="urn:s"><s:p><s:t>머리</s:t>'
                '<s:tbl><s:tc><s:p><s:t>셀1</s:t></s:p></s:tc>'
                '<s:tc><s:p><s:t>셀2</s:t></s:p></s:tc></s:tbl>'
                '<s:t>꼬리</s:t></s:p></s:sec>',
            )
        ]
    )
    assert extract_hwpx_paragraphs(path) == ["머리꼬리", "셀1", "셀2"]


def test_empty_outer_and_inner_paragraphs_preserved(make_hwpx: SourceFactory) -> None:
    path = make_hwpx([(0, "<sec><p><p><t>A</t></p><p/></p><p><t>B</t></p></sec>")])
    assert extract_hwpx_paragraphs(path) == ["", "A", "", "B"]


def test_identical_text_in_distinct_paragraphs_preserved(
    make_hwpx: SourceFactory,
) -> None:
    path = make_hwpx([(0, "<sec><p><t>동일</t></p><p><t>동일</t></p></sec>")])
    assert extract_hwpx_paragraphs(path) == ["동일", "동일"]


def test_nested_span_inside_t_keeps_whitespace_and_unicode(
    make_hwpx: SourceFactory,
) -> None:
    path = make_hwpx(
        [
            (
                0,
                "<sec><p><t>  한글<span>중첩</span> 끝\t</t>"
                "<box><p><t>자식</t></p></box></p></sec>",
            )
        ]
    )
    assert extract_hwpx_paragraphs(path) == ["  한글중첩 끝\t", "자식"]


def test_numeric_section_order_and_nested_boundaries(make_hwpx: SourceFactory) -> None:
    path = make_hwpx(
        [
            (10, "<sec><p><t>10</t></p></sec>"),
            (2, "<sec><p><t>2</t><p><t>2중첩</t></p></p></sec>"),
            (0, "<sec><p><t>0</t></p></sec>"),
        ]
    )
    assert extract_hwpx_paragraphs(path) == ["0", "2", "2중첩", "10"]


def test_outside_text_not_misattributed(make_hwpx: SourceFactory) -> None:
    path = make_hwpx([(0, "<sec><t>바깥</t><p><t>안쪽</t></p></sec>")])
    assert extract_hwpx_paragraphs(path) == ["안쪽"]


def test_non_nested_document_unchanged(make_hwpx: SourceFactory) -> None:
    path = make_hwpx(
        [(0, "<sec><p><t>A</t><t> B</t></p><p/><p><t>C</t></p></sec>")]
    )
    assert extract_hwpx_paragraphs(path) == ["A B", "", "C"]
```

## 5. 준비·실행 지침 (Codex용)

1. `AGENTS.md` 및 최신 공통 개발지침을 읽고 현재 main HEAD와 작업 트리 상태를 확인한다. 보호 대상에 미커밋 변경이 있으면 중단한다.
2. `fix/doc-parser-ot1-nested-paragraphs` 별도 브랜치에서만 작업한다. `main`과 과거 G2-R1 기록은 변경하지 않는다.
3. 현재 기준 코드와 이 STEP의 기능 계약을 대조하고 위 운영 코드·신규 합성 테스트만 적용한다. `DOC-PARSER-2.md`는 원본 그대로 보존한다.
4. 서식 검사 **Black 26.10.1 기준**을 확인한다. 새 테스트 파일만 Black으로 정리할 수 있다. 검증 코드를 삭제하거나 테스트 기준을 완화하지 않는다.
5. 변경 파일 목록을 확인하고 허용된 경로 외 변경이 있으면 중단한다.
6. 합성 테스트 및 기존 Parser 테스트와 Ruff/Black, 저장소 전체 회귀 테스트를 실행한다.
7. 실제 OT1-001 문서는 **사용자 로컬에서만** 읽기 전용으로 실행한다. 원문·경로·추출 텍스트·XML을 AI, 채팅, Git, 원격 로그에 넣지 않는다. 문단 수·길이 합계·빈 문단 수·원본 SHA-256 동일 여부만 비교한다.
8. 실제 문서 대조·추가 2종 이상의 비민감 문서 검증이 끝나기 전에는 DOC-PARSER-2 운영 완료를 선언하지 않는다.
9. 외부 확인 후 결과 MD에 정확한 실행 결과만 기록한다. 승인 전 push/merge/deploy 금지.

### 로컬 실행 명령 (저장소 루트)

```powershell
# 실제 작업 중인 worktree가 올바른지 확인
python -c "import document_parser.paragraphs as p; print(p.__file__)"

# 이전 Windows 앱 제어 오류를 고려해 Python -m 사용
uv run --project apps/document-parser python -m pytest apps/document-parser/tests -q
uv run --project apps/document-parser ruff check apps/document-parser/src/document_parser apps/document-parser/tests
uv run --project apps/document-parser python -m black --check apps/document-parser/src/document_parser apps/document-parser/tests

# 프로젝트 전체 회귀
uv run python -m pytest -q

git status --short
git diff --name-only
```

`uv`가 환경을 새로 동기화하려 할 때는 이전에 검증한 `UV_NO_SYNC=1`, `UV_PROJECT_ENVIRONMENT`, `PYTHONPATH` 값을 사용하되, Python import가 **해당 작업 브랜치**의 소스를 가리키는지 확인한다. 환경 보안 설정을 임의 변경하지 않는다.

### OT1-001 실제 문서 요약 검사 (민감 내용 출력 금지)

PowerShell에서 개인 PC의 **로컬 HWPX 경로만** 환경 변수로 지정하고 아래 코드 실행한다. 어떤 경로도 Git에 올리지 않는다.

```powershell
$env:DOC_PARSER_FILE = "C:\local-private\OT1-001.hwpx"  # 실제 로컬 경로로 변경
@'
import hashlib
import os
from pathlib import Path
from document_parser.paragraphs import extract_hwpx_paragraphs

path = Path(os.environ["DOC_PARSER_FILE"])
before = hashlib.sha256(path.read_bytes()).hexdigest()
items = extract_hwpx_paragraphs(path)
after = hashlib.sha256(path.read_bytes()).hexdigest()
print("paragraph_count:", len(items))
print("character_count:", sum(map(len, items)))
print("empty_paragraph_count:", sum(not item for item in items))
print("original_unchanged:", before == after)
assert before == after
'@ | uv run --project apps/document-parser python -
```

기존 OT1-001과 **동일한 파일**이고 모든 추출 대상 `t`가 `p` 아래에 있다면 문단 147개, 문자 합계 약 3,476자(중복 집계 0자)가 목표다. 이는 **예상 기준**이며 실제 검증 결과가 아니다. 일치하지 않으면 원인을 로컬에서 분석하고 실패/미확정으로 기록한다.

## 6. 검증 성공 기준

| Gate | 합격 기준 |
|---|---|
| 합성 신규 테스트 | 중첩 문단 3단계, 표 내부 문단, 동문 반복, 빈 문단, 공백, 숫자 구역 순서 등 모두 PASS |
| 기존 Parser 테스트 | 기존 99개 회귀 테스트 보존 및 통과 (테스트 변경·삭제 불가) |
| Ruff/Black | 모두 PASS |
| 저장소 전체 회귀 | 새 실패 없음 |
| 기존 API | 입력 검증, 예외 메시지·원인, 섹션 경계, `extract_hwpx_text` 동작 불변 |
| 실제 OT1-001 | 원본 SHA-256 동일; 중첩된 텍스트 반복 집계 사라짐, 내용/순서 사람 대조 |
| 운영 완료 | 실제 문서 3종 이상, 사람 대조까지 완료 후에만 판정 |

## 7. 제공 당시의 사전 점검 결과와 미검증 사항

- 이 문서에 포함된 수정 로직은 **별도 재현 환경에서 합성 회귀 테스트 8개 PASS, Python 문법 검사 PASS**.
- 원본 GitHub 작업 브랜치에 코드 적용하지 않음. 원본 Parser 99개/저장소 전체 회귀, Ruff, Black, 실제 OT1-001 검사 **아직 미실행**.
- 결과 문서에는 위 미검증 항목을 PASS로 표시하지 않는다.

## 8. 다음 STEP

FIX1 정상 반영 후 `DOC-PARSER-OT1-R2` 실제 문서 재검증 (기존 OT1-001 및 다른 비민감 문서 2종 이상), 운영 완료 판정 후 `DOC-PARSER-UI1` 최소 로컬 웹 UI 검토.

## 9. 실제 FIX1 코드 검증 — 2026-11-03

- 기준 main: `4d8e4308bcf4ab7fbf994928708527bcdcda09ce` (원격 재확인).
- 작업 브랜치: `fix/doc-parser-ot1-nested-paragraphs`, 별도 worktree 사용.
- 신규 테스트로 기존 코드의 중복 집계 재현: 수정 전 **5 failed, 3 passed**.
- FIX1 적용 후 신규 합성 테스트: **8 passed** (2.70초).
- 기존 99개를 수정하지 않고 포함한 Parser 회귀: **107 passed** (0.33초).
- 저장소 전체 회귀: **348 passed, 1 skipped** (61.12초).
- Parser Ruff 및 Black: 통과, 10 files unchanged.
- 저장소 전체 Ruff 및 Black: 통과, 253 files unchanged.
- 변경 경로는 paragraphs.py, 신규 중첩 테스트, 이 보완 명세 3개뿐이다.
- 신규 테스트에 Black 서식만 적용했으며 제공본과 AST가 동일함을 확인했다.
- 기존 테스트/보호 모듈/원본 DOC-PARSER-2.md는 main과 동일하며, 이전 실패 증거 8개의 SHA-256도 동일하다.
- 실제 HWPX는 이번 단계에서 읽지 않았다. OT1-001의 문단 수·문자 합계·원본 불변·사람 대조와 추가 2종 검증은 **미실행/미검증**이다.
- 임의 운영 결과 PASS, main 병합, Push, 배포, 다음 STEP 개발은 하지 않았다.
- 실제 운영 재검증 전이므로 `DOC-PARSER-OT1-FIX1-result.md`는 아직 작성하지 않는다. 위 값은 코드/합성 회귀 결과다.
