"""Verify paragraph extraction using synthetic ZIP/XML sources only."""

import os
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

import pytest

from document_parser import DocumentSource, inspect_document_source, paragraphs


@pytest.fixture
def source_path(tmp_path: Path) -> Path:
    """Provide a temporary path for a synthetic HWPX source."""
    return tmp_path / "sample.HWPX"


def test_multiple_paragraphs(source_path: Path) -> None:
    """Keep paragraph order and concatenate text across runs without separators."""
    with ZipFile(source_path, "w") as output:
        output.writestr(
            "Contents/section0.xml",
            '<hp:sec xmlns:hp="urn:test"><hp:t>outside</hp:t>'
            "<hp:p><hp:run><hp:t>First</hp:t></hp:run>"
            "<hp:run><hp:t> paragraph</hp:t></hp:run></hp:p>"
            "<hp:group><hp:p><hp:t>Second</hp:t></hp:p></hp:group>"
            "<hp:p>ignored<hp:t>Third</hp:t>ignored</hp:p></hp:sec>",
        )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == [
        "First paragraph",
        "Second",
        "Third",
    ]
    assert source_path.read_bytes() == before


def test_numeric_section_order(source_path: Path) -> None:
    """Sort section numbers independently of archive and lexical order."""
    with ZipFile(source_path, "w") as output:
        for number in [10, 2, 0]:
            output.writestr(
                f"Contents/section{number}.xml",
                f"<sec><p><t>{number}a</t></p><p><t>{number}b</t></p></sec>",
            )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == [
        "0a",
        "0b",
        "2a",
        "2b",
        "10a",
        "10b",
    ]
    assert source_path.read_bytes() == before


def test_whitespace_and_unicode(source_path: Path) -> None:
    """Preserve Unicode, nested text, tabs, newlines and surrounding spaces."""
    with ZipFile(source_path, "w") as output:
        output.writestr(
            "Contents/section0.xml",
            '<sec xmlns="urn:default"><p><t>  한글 '
            "<span>중첩</span> 끝 </t><t>\t다음\n</t></p>"
            "<p><t> \t\n </t></p></sec>",
        )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == [
        "  한글 중첩 끝 \t다음\n",
        " \t\n ",
    ]
    assert source_path.read_bytes() == before


def test_empty_paragraphs(source_path: Path) -> None:
    """Retain paragraphs with no text alongside nonempty paragraphs."""
    with ZipFile(source_path, "w") as output:
        output.writestr(
            "Contents/section0.xml",
            "<sec><p/><p><t/></p><p><t>body</t></p><p>ignored</p></sec>",
        )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == ["", "", "body", ""]
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("xml", ["<sec/>", "<sec><t>outside</t></sec>"])
def test_sections_without_paragraphs(source_path: Path, xml: str) -> None:
    """Return an empty list when matching sections contain no paragraphs."""
    with ZipFile(source_path, "w") as output:
        output.writestr("Contents/section0.xml", xml)
        output.writestr("Contents/section1.xml", "<sec/>")
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == []
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("as_string", [False, True])
def test_public_api_reuse(
    source_path: Path, monkeypatch: pytest.MonkeyPatch, as_string: bool
) -> None:
    """Use the real public validator and open its expanded path read-only."""
    monkeypatch.setenv(
        "USERPROFILE" if os.name == "nt" else "HOME", str(source_path.parent)
    )
    with ZipFile(source_path, "w") as output:
        output.writestr("Contents/section0.xml", "<sec><p><t>본문</t></p></sec>")
    before = source_path.read_bytes()
    relative_path = Path("~") / source_path.name
    file_path = str(relative_path) if as_string else relative_path

    with patch.object(
        paragraphs, "inspect_document_source", wraps=inspect_document_source
    ) as inspected:
        with patch.object(paragraphs, "ZipFile", wraps=ZipFile) as opened:
            assert paragraphs.extract_hwpx_paragraphs(file_path) == ["본문"]
    inspected.assert_called_once_with(file_path)
    opened.assert_called_once_with(source_path, "r")
    assert inspect_document_source(file_path) == DocumentSource(source_path, "hwpx")
    assert source_path.read_bytes() == before
