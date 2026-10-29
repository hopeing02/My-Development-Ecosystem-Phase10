"""Verify minimal extraction with synthetic ZIP/XML held entirely in memory."""

import os
from collections.abc import Callable, Iterator
from io import BytesIO
from os import stat_result
from pathlib import Path
from stat import S_IFREG
from unittest.mock import Mock, patch
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

import pytest

from document_parser import DocumentSource, inspect_document_source
from document_parser import hwpx

SOURCE_PATH = Path("일반 문서.HWPX")


@pytest.fixture
def archive() -> BytesIO:
    """Provide a synthetic archive without creating files or extracting ZIPs."""
    return BytesIO()


@pytest.fixture
def source_stat() -> Iterator[Mock]:
    """Let the real public input API inspect a regular synthetic source."""
    metadata = stat_result((S_IFREG | 0o444, 0, 0, 1, 0, 0, 123, 0, 0, 0))
    with patch.object(Path, "stat", return_value=metadata) as mocked:
        yield mocked


@pytest.fixture
def extract(archive: BytesIO, source_stat: Mock) -> Callable[[str | Path], str]:
    """Route read-only source opens to the in-memory archive, preserving bytes."""

    def run(file_path: str | Path = SOURCE_PATH) -> str:
        before = archive.getvalue()
        with patch.object(hwpx, "ZipFile", return_value=ZipFile(archive)) as opened:
            result = hwpx.extract_hwpx_text(file_path=file_path)
        opened.assert_called_once_with(inspect_document_source(file_path).path, "r")
        assert archive.getvalue() == before
        return result

    return run


@pytest.mark.parametrize("as_string", [False, True])
def test_text_and_public_api_reuse(
    archive: BytesIO, extract: Callable[[str | Path], str], as_string: bool
) -> None:
    """Call the real input API and preserve Unicode, nested text and spaces."""
    with ZipFile(archive, "w") as output:
        output.writestr(
            "Contents/section0.xml",
            '<hp:sec xmlns:hp="urn:test"><hp:p><hp:t>  한글 '
            "<hp:span>중첩</hp:span> 끝 </hp:t><hp:t/>"
            "<hp:t>\t다음\n</hp:t></hp:p></hp:sec>",
        )
    path = str(SOURCE_PATH) if as_string else SOURCE_PATH
    with patch.object(
        hwpx, "inspect_document_source", wraps=inspect_document_source
    ) as inspected:
        assert extract(path) == "  한글 중첩 끝 \t다음\n"
    inspected.assert_called_once_with(path)
    assert inspect_document_source(path) == DocumentSource(SOURCE_PATH, "hwpx")


def test_numeric_order_and_exact_section_names(
    archive: BytesIO, extract: Callable[[str | Path], str]
) -> None:
    """Sort numbers independently of ZIP order and ignore near-match members."""
    with ZipFile(archive, "w") as output:
        for number in [10, 2, 0]:
            output.writestr(
                f"Contents/section{number}.xml", f"<sec><t>{number}</t></sec>"
            )
        for name in [
            "Contents/header.xml",
            "Other/section1.xml",
            "Contents/Section1.xml",
            "Contents/section1.xml.bak",
            "Contents/section-1.xml",
            "Contents/section1.xml\n",
            "prefix/Contents/section1.xml",
            "Contents/sub/section1.xml",
        ]:
            output.writestr(name, "not XML")
    assert extract(SOURCE_PATH) == "0\n2\n10"


@pytest.mark.parametrize(
    "xml",
    [
        '<x:sec xmlns:x="urn:other"><x:t>본문</x:t></x:sec>',
        '<sec xmlns="urn:default"><t>본문</t></sec>',
        "<sec><t>본문</t></sec>",
    ],
)
def test_namespace_independence(
    archive: BytesIO, extract: Callable[[str | Path], str], xml: str
) -> None:
    """Recognize text elements by local name with any or no namespace."""
    with ZipFile(archive, "w") as output:
        output.writestr("Contents/section0.xml", xml)
    assert extract(SOURCE_PATH) == "본문"


@pytest.mark.parametrize("middle", ["<sec/>", "<sec><t/></sec>"])
def test_empty_sections(
    archive: BytesIO, extract: Callable[[str | Path], str], middle: str
) -> None:
    """Retain empty sections and insert only the required section separators."""
    with ZipFile(archive, "w") as output:
        output.writestr("Contents/section0.xml", "<sec><t>A</t></sec>")
        output.writestr("Contents/section1.xml", middle)
        output.writestr("Contents/section2.xml", "<sec><t>B</t></sec>")
    assert extract(SOURCE_PATH) == "A\n\nB"


def test_single_empty_section(
    archive: BytesIO, extract: Callable[[str | Path], str]
) -> None:
    """Return an empty string when the only section has no text."""
    with ZipFile(archive, "w") as output:
        output.writestr("Contents/section0.xml", "<sec>ignored<t/></sec>")
    assert extract(SOURCE_PATH) == ""


def test_home_expansion(
    archive: BytesIO,
    extract: Callable[[str | Path], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Open the expanded path supplied by the public input API."""
    monkeypatch.setenv("USERPROFILE" if os.name == "nt" else "HOME", str(Path.cwd()))
    with ZipFile(archive, "w") as output:
        output.writestr("Contents/section0.xml", "<sec><t>본문</t></sec>")
    assert extract("~/sample.hwpx") == "본문"


@pytest.mark.parametrize("suffix", [".pdf", ".hwp"])
def test_non_hwpx_source(source_stat: Mock, suffix: str) -> None:
    """Reject supported non-HWPX sources before opening their contents."""
    with patch.object(hwpx, "ZipFile") as opened:
        with pytest.raises(ValueError, match="Expected HWPX"):
            hwpx.extract_hwpx_text(f"sample{suffix}")
    opened.assert_not_called()


@pytest.mark.parametrize(
    "error", [FileNotFoundError("missing"), PermissionError("denied")]
)
def test_source_error_propagation(source_stat: Mock, error: OSError) -> None:
    """Propagate errors from the actual public source validation unchanged."""
    source_stat.side_effect = error
    with patch.object(hwpx, "ZipFile") as opened:
        with pytest.raises(type(error)) as caught:
            hwpx.extract_hwpx_text(SOURCE_PATH)
    assert caught.value is error
    opened.assert_not_called()


@pytest.mark.parametrize("file_path", [None, 42, b"sample.hwpx"])
def test_invalid_path_type(file_path: object) -> None:
    """Let the public input API reject invalid types before content access."""
    with patch.object(hwpx, "ZipFile") as opened:
        with pytest.raises(TypeError):
            hwpx.extract_hwpx_text(file_path)
    opened.assert_not_called()


def test_invalid_zip(source_stat: Mock) -> None:
    """Translate an actual ZIP parsing error while retaining its cause."""
    with patch.object(
        hwpx,
        "ZipFile",
        side_effect=lambda path, mode: ZipFile(BytesIO(b"not ZIP"), mode),
    ):
        with pytest.raises(ValueError, match="Invalid HWPX ZIP") as caught:
            hwpx.extract_hwpx_text(SOURCE_PATH)
    assert isinstance(caught.value.__cause__, BadZipFile)


def test_no_sections(archive: BytesIO, source_stat: Mock) -> None:
    """Reject an archive without matching section members."""
    with ZipFile(archive, "w") as output:
        output.writestr("Contents/header.xml", "<header/>")
    with patch.object(hwpx, "ZipFile", return_value=ZipFile(archive)):
        with pytest.raises(ValueError, match="no section XML"):
            hwpx.extract_hwpx_text(SOURCE_PATH)


def test_invalid_xml(archive: BytesIO, source_stat: Mock) -> None:
    """Include the broken section member and preserve the XML parser cause."""
    member = "Contents/section2.xml"
    with ZipFile(archive, "w") as output:
        output.writestr(member, "<sec><t>broken</sec>")
    with patch.object(hwpx, "ZipFile", return_value=ZipFile(archive)):
        with pytest.raises(ValueError, match="Invalid HWPX section XML") as caught:
            hwpx.extract_hwpx_text(SOURCE_PATH)
    assert member in str(caught.value)
    assert isinstance(caught.value.__cause__, ParseError)
