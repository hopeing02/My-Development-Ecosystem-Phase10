STEP DOC-PARSER-1 — HWPX 최소 텍스트 추출
1. 이번 단계의 목표
검증 완료된 DOC-PARSER-0의 inspect_document_source()를 그대로 재사용하여 .hwpx 문서에서 본문 텍스트만 최소 추출한다.
한컴 공식 HWPX 구조상 HWPX는 ZIP/XML 기반이며, Contents/section0.xml, section1.xml, ... 에 구역별 본문이 저장되고 본문 문자열은 <hp:t> 요소에 들어간다.
이번 STEP에서는 이 구조만 사용한다.
HWPX 파일
↓
DOC-PARSER-0 inspect_document_source()
↓
ZIP 열기
↓
Contents/sectionN.xml 숫자 순 정렬
↓
<t> 텍스트 추출
↓
section 단위 문자열 연결
↓
str 반환
2. 기존 기능 재사용
재사용:
apps/document-parser/src/document_parser/source.py
DocumentSource
inspect_document_source()
위 검증 완료 파일은 수정하지 않는다.
__init__.py도 수정하지 않는다.
3. 변경 파일
신규
apps/document-parser/src/document_parser/hwpx.py
apps/document-parser/tests/test_hwpx.py
docs/15_projects/document-parser/implementation/DOC-PARSER-1.md
기존 파일 변경 없음.
4. 운영 코드
apps/document-parser/src/document_parser/hwpx.py
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .source import inspect_document_source

_SECTION_PATTERN = re.compile(r"^Contents/section(\d+)\.xml$")


def extract_hwpx_text(file_path: str | Path) -> str:
    """Extract plain text from HWPX section XML files in document order."""
    source = inspect_document_source(file_path)
    if source.format != "hwpx":
        raise ValueError(f"Expected HWPX document, got: {source.format}")

    try:
        with zipfile.ZipFile(source.path) as archive:
            sections: list[tuple[int, str]] = []

            for name in archive.namelist():
                match = _SECTION_PATTERN.fullmatch(name)
                if match is not None:
                    sections.append((int(match.group(1)), name))

            if not sections:
                raise ValueError("HWPX document has no section XML files")

            section_texts: list[str] = []

            for _, section_name in sorted(sections):
                try:
                    root = ET.fromstring(archive.read(section_name))
                except ET.ParseError as exc:
                    raise ValueError(
                        f"Invalid HWPX section XML: {section_name}"
                    ) from exc

                text_parts = [
                    "".join(element.itertext())
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "t"
                ]
                section_texts.append("".join(text_parts))

    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid HWPX ZIP container") from exc

    return "\n".join(section_texts)
apps/document-parser/tests/test_hwpx.py
from pathlib import Path
import zipfile

import pytest

from document_parser.hwpx import extract_hwpx_text

HP_NAMESPACE = "http://www.hancom.co.kr/hwpml/2011/paragraph"


def _write_hwpx(path: Path, sections: dict[int, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for index, body in sections.items():
            archive.writestr(
                f"Contents/section{index}.xml",
                f'<hp:sec xmlns:hp="{HP_NAMESPACE}">{body}</hp:sec>',
            )


def test_extracts_text_from_multiple_runs(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.hwpx"
    _write_hwpx(
        document_path,
        {
            0: (
                "<hp:p>"
                "<hp:run><hp:t>한글</hp:t></hp:run>"
                "<hp:run><hp:t>과</hp:t></hp:run>"
                "<hp:run><hp:t>컴퓨터</hp:t></hp:run>"
                "</hp:p>"
            )
        },
    )

    assert extract_hwpx_text(document_path) == "한글과컴퓨터"


def test_orders_sections_numerically(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.hwpx"

    with zipfile.ZipFile(document_path, "w") as archive:
        archive.writestr(
            "Contents/section1.xml",
            (
                f'<hp:sec xmlns:hp="{HP_NAMESPACE}">'
                "<hp:p><hp:run><hp:t>둘째</hp:t></hp:run></hp:p>"
                "</hp:sec>"
            ),
        )
        archive.writestr(
            "Contents/section0.xml",
            (
                f'<hp:sec xmlns:hp="{HP_NAMESPACE}">'
                "<hp:p><hp:run><hp:t>첫째</hp:t></hp:run></hp:p>"
                "</hp:sec>"
            ),
        )

    assert extract_hwpx_text(document_path) == "첫째\n둘째"


def test_rejects_non_hwpx_input(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.pdf"
    document_path.write_bytes(b"%PDF")

    with pytest.raises(ValueError, match="Expected HWPX"):
        extract_hwpx_text(document_path)


def test_rejects_invalid_zip(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.hwpx"
    document_path.write_text("not zip", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid HWPX ZIP"):
        extract_hwpx_text(document_path)


def test_rejects_missing_section_xml(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.hwpx"

    with zipfile.ZipFile(document_path, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")

    with pytest.raises(ValueError, match="no section XML"):
        extract_hwpx_text(document_path)


def test_rejects_invalid_section_xml(tmp_path: Path) -> None:
    document_path = tmp_path / "sample.hwpx"

    with zipfile.ZipFile(document_path, "w") as archive:
        archive.writestr("Contents/section0.xml", "<hp:sec>")

    with pytest.raises(ValueError, match="Invalid HWPX section XML"):
        extract_hwpx_text(document_path)
5. 동작 기준
.hwpx가 아니면 기존 inspect_document_source() 결과를 이용해 거부한다.
HWPX ZIP의 Contents/sectionN.xml만 읽는다.
section 번호를 숫자로 정렬한다.
XML namespace prefix 자체에 의존하지 않고 local-name t를 추출한다.
같은 section의 텍스트는 그대로 이어 붙인다.
section 사이에만 \n 하나를 넣는다.
원본 문서는 수정하지 않는다.
6. 실행 및 검증
uv run --project apps/document-parser pytest `
  apps/document-parser/tests/test_source.py `
  apps/document-parser/tests/test_hwpx.py

uv run --project apps/document-parser ruff check `
  apps/document-parser/src/document_parser `
  apps/document-parser/tests

uv run --project apps/document-parser black --check `
  apps/document-parser/src/document_parser `
  apps/document-parser/tests
이 답변에서 제시한 신규 hwpx.py + test_hwpx.py 최소 코드는 격리 테스트에서 6 passed를 확인했다.
최종 검증 완료 판정은 실제 MDE/Codex Windows 저장소에서 위 검증 Gate가 PASS한 뒤 한다.
7. 성공 기준
DOC-PARSER-0 회귀 테스트 PASS
한 section의 여러 <hp:t> 텍스트 연결 성공
section0 → section1 숫자 순서 유지
PDF 등 비-HWPX 입력 거부
잘못된 ZIP 거부
section XML 없는 HWPX 거부
잘못된 XML 거부
Ruff PASS
Black PASS
disallowedFiles 0건
8. 보안 확인
읽기 전용 처리
원본 문서 수정 없음
외부 전송 없음
기관 내부 문서 사용 금지
테스트는 합법적으로 외부 사용 가능한 자료만 사용
비밀키/API Key 없음
9. 이번 단계에서 하지 않는 것
문단 경계 보존
제목/본문/주석 구조 판정
Bold/FontSize/Indent 분석
header.xml 서식 매핑
표 Parser
이미지 Parser
HWP 바이너리 Parser
PDF Parser
OCR
NormalizedDocument 공통 Core
검색/색인
AI/RAG/Vector DB
신규 오케스트레이션 Framework
10. MDE-CODEX-W1 작업 JSON
{
  "taskId": "DOC-PARSER-001",
  "stepId": "DOC-PARSER-1",
  "projectPath": ".",
  "requirement": "DOC-PARSER-0 검증 완료 코드를 재작성하지 않고 그대로 재사용하여 HWPX 최소 텍스트 추출을 구현한다. 기존 apps/document-parser/src/document_parser/source.py의 inspect_document_source()를 반드시 재사용하고 source.py와 __init__.py는 수정하지 않는다. Python 표준 라이브러리 zipfile과 xml.etree.ElementTree만 사용한다. HWPX ZIP 내부의 Contents/sectionN.xml 파일을 N의 숫자 순서대로 읽고, 각 section XML에서 local-name이 t인 텍스트 요소의 내용을 문서 순서대로 이어 붙인다. 같은 section 안에서는 텍스트를 그대로 연결하고 section 사이에만 줄바꿈 1개를 넣어 문자열로 반환한다. 잘못된 HWPX ZIP, section XML 부재, 잘못된 section XML은 명확한 ValueError로 처리한다. 이번 STEP에서는 문단 분리, 서식, 표, 이미지, header.xml 스타일 매핑, OCR, HWP 바이너리 파싱, PDF 파싱, AI/RAG/Vector DB/API/새 Framework를 구현하지 않는다. 기관 내부 코드·문서·경로·업무규칙을 사용하지 않는다. 작업 전에 AGENTS.md와 저장소의 최신 거버넌스/개발지침을 확인하고, 허용 파일 밖은 수정하지 않는다.",
  "allowedFiles": [
    "apps/document-parser/src/document_parser/hwpx.py",
    "apps/document-parser/tests/test_hwpx.py",
    "docs/15_projects/document-parser/implementation/DOC-PARSER-1.md"
  ],
  "validationCommands": [
    [
      "uv",
      "run",
      "--project",
      "apps/document-parser",
      "pytest",
      "apps/document-parser/tests/test_source.py",
      "apps/document-parser/tests/test_hwpx.py"
    ],
    [
      "uv",
      "run",
      "--project",
      "apps/document-parser",
      "ruff",
      "check",
      "apps/document-parser/src/document_parser",
      "apps/document-parser/tests"
    ],
    [
      "uv",
      "run",
      "--project",
      "apps/document-parser",
      "black",
      "--check",
      "apps/document-parser/src/document_parser",
      "apps/document-parser/tests"
    ]
  ],
  "timeoutSeconds": 1800
}
11. 다음 STEP
DOC-PARSER-2 — HWPX 문단 분리
검증 완료된 extract_hwpx_text()를 재작성하지 않고, HWPX의 <hp:p> 단위를 별도 구조로 추출하는 최소 기능을 추가한다.
