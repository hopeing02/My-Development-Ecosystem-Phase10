"""Verify HWPX paragraph boundaries with synthetic sources only."""

from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

import pytest

from document_parser import inspect_document_source, paragraphs

SourceFactory = Callable[[list[tuple[str, str]]], Path]

NEAR_MATCH_MEMBERS = (
    "Contents/header.xml",
    "Other/section1.xml",
    "contents/section1.xml",
    "Contents/Section1.xml",
    "Contents/section.xml",
    "Contents/section-1.xml",
    "Contents/section+1.xml",
    "Contents/section1.0.xml",
    "Contents/section1.XML",
    "Contents/section1.xml.bak",
    "Contents/section1.xml\n",
    "Contents/section1.xml/",
    "prefix/Contents/section1.xml",
    "Contents/sub/section1.xml",
)


@pytest.fixture
def make_source(tmp_path: Path) -> SourceFactory:
    """Build a real temporary source containing only synthetic ZIP members."""

    def create(members: list[tuple[str, str]]) -> Path:
        source_path = tmp_path / "synthetic.HWPX"
        with ZipFile(source_path, "w") as output:
            for name, xml in members:
                output.writestr(name, xml)
        return source_path

    return create


@pytest.mark.parametrize(
    "xml",
    [
        "<sec><p><t>A<span>β</span></t></p><p/></sec>",
        '<x:sec xmlns:x="urn:alternate"><x:p><x:t>A<x:span>β</x:span>'
        "</x:t></x:p><x:p/></x:sec>",
        '<sec xmlns="urn:default"><p><t>A<span>β</span></t></p><p/></sec>',
        '<sec xmlns:p="urn:paragraph" xmlns:t="urn:text">'
        "<p:p><t:t>A<span>β</span></t:t></p:p><p:p/></sec>",
    ],
)
def test_namespace_variants(make_source: SourceFactory, xml: str) -> None:
    """Recognize paragraph and text local names across independent namespaces."""
    source_path = make_source([("Contents/section0.xml", xml)])
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == ["Aβ", ""]
    assert source_path.read_bytes() == before


@pytest.mark.parametrize(
    "empty_xml", ["<sec/>", "<sec><t>outside</t></sec>", "<sec><group/></sec>"]
)
def test_empty_sections_between_paragraphs(
    make_source: SourceFactory, empty_xml: str
) -> None:
    """Skip empty sections while retaining an explicitly empty paragraph."""
    source_path = make_source(
        [
            ("Contents/section5.xml", empty_xml),
            ("Contents/section4.xml", "<sec><p><t>B</t></p></sec>"),
            ("Contents/section3.xml", "<sec><p/></sec>"),
            ("Contents/section2.xml", empty_xml),
            ("Contents/section1.xml", "<sec><p><t>A</t></p></sec>"),
            ("Contents/section0.xml", empty_xml),
        ]
    )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == ["A", "", "B"]
    assert source_path.read_bytes() == before


def test_all_sections_without_paragraphs(make_source: SourceFactory) -> None:
    """Return no paragraphs when every matching section lacks p elements."""
    source_path = make_source(
        [
            ("Contents/section10.xml", "<sec><t>outside</t></sec>"),
            ("Contents/section2.xml", '<sec xmlns="urn:empty"><group/></sec>'),
            ("Contents/section0.xml", "<sec/>"),
        ]
    )
    before = source_path.read_bytes()

    assert paragraphs.extract_hwpx_paragraphs(source_path) == []
    assert source_path.read_bytes() == before


def test_exact_section_names_and_read_only_access(make_source: SourceFactory) -> None:
    """Ignore malformed near matches and sort accepted numeric section names."""
    members = [(name, "not XML") for name in NEAR_MATCH_MEMBERS]
    members.extend(
        [
            ("Contents/section10.xml", "<sec><p><t>ten</t></p></sec>"),
            ("Contents/section0002.xml", "<sec><p><t>two</t></p></sec>"),
            ("Contents/section0.xml", "<sec><p><t>zero</t></p></sec>"),
        ]
    )
    source_path = make_source(members)
    before = source_path.read_bytes()

    with patch.object(paragraphs, "ZipFile", wraps=ZipFile) as opened:
        with patch.object(ZipFile, "extract") as extracted:
            with patch.object(ZipFile, "extractall") as extracted_all:
                assert paragraphs.extract_hwpx_paragraphs(source_path) == [
                    "zero",
                    "two",
                    "ten",
                ]
    opened.assert_called_once_with(source_path, "r")
    extracted.assert_not_called()
    extracted_all.assert_not_called()
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("member", NEAR_MATCH_MEMBERS)
def test_near_match_is_not_a_section(make_source: SourceFactory, member: str) -> None:
    """Require an exact section member even when a near match contains XML."""
    source_path = make_source([(member, "<sec><p><t>ignored</t></p></sec>")])
    before = source_path.read_bytes()

    with pytest.raises(ValueError, match="no section XML") as caught:
        paragraphs.extract_hwpx_paragraphs(source_path)
    assert caught.value.__cause__ is None
    assert source_path.read_bytes() == before


def test_empty_archive_has_no_sections(make_source: SourceFactory) -> None:
    """Reject a valid ZIP containing no members."""
    source_path = make_source([])
    before = source_path.read_bytes()

    with pytest.raises(ValueError, match="no section XML"):
        paragraphs.extract_hwpx_paragraphs(source_path)
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("suffix", [".pdf", ".hwp", ".PDF", ".HWP"])
def test_supported_non_hwpx_is_rejected_before_open(
    tmp_path: Path, suffix: str
) -> None:
    """Reject other supported formats before attempting ZIP access."""
    source_path = tmp_path / f"synthetic{suffix}"
    source_path.write_bytes(b"synthetic non-ZIP source")
    before = source_path.read_bytes()

    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(ValueError, match="Expected HWPX"):
            paragraphs.extract_hwpx_paragraphs(source_path)
    opened.assert_not_called()
    assert source_path.read_bytes() == before


@pytest.mark.parametrize("contents", [b"", b"not a ZIP archive"])
def test_bad_zip_retains_original_cause(tmp_path: Path, contents: bytes) -> None:
    """Translate actual ZIP parsing failures without modifying source bytes."""
    source_path = tmp_path / "broken.hwpx"
    source_path.write_bytes(contents)

    with pytest.raises(ValueError, match="Invalid HWPX ZIP") as caught:
        paragraphs.extract_hwpx_paragraphs(source_path)
    assert isinstance(caught.value.__cause__, BadZipFile)
    assert source_path.read_bytes() == contents


@pytest.mark.parametrize("xml", ["", "<sec><p><t>broken</sec>"])
def test_bad_xml_identifies_section_and_retains_cause(
    make_source: SourceFactory, xml: str
) -> None:
    """Report the broken section even after a preceding section was parsed."""
    member = "Contents/section2.xml"
    source_path = make_source(
        [
            (member, xml),
            ("Contents/section0.xml", "<sec><p><t>valid</t></p></sec>"),
        ]
    )
    before = source_path.read_bytes()

    with pytest.raises(ValueError, match="Invalid HWPX section XML") as caught:
        paragraphs.extract_hwpx_paragraphs(source_path)
    assert member in str(caught.value)
    assert isinstance(caught.value.__cause__, ParseError)
    assert source_path.read_bytes() == before


@pytest.mark.parametrize(
    "error", [FileNotFoundError("missing"), PermissionError("denied")]
)
def test_validation_error_propagates_unchanged(tmp_path: Path, error: OSError) -> None:
    """Preserve filesystem errors raised through the real public validator."""
    source_path = tmp_path / "synthetic.hwpx"

    with patch.object(Path, "stat", side_effect=error):
        with patch.object(
            paragraphs, "inspect_document_source", wraps=inspect_document_source
        ) as inspected:
            with patch.object(paragraphs, "ZipFile") as opened:
                with pytest.raises(type(error)) as caught:
                    paragraphs.extract_hwpx_paragraphs(source_path)
    assert caught.value is error
    inspected.assert_called_once_with(source_path)
    opened.assert_not_called()


def test_missing_source_is_rejected_before_open(tmp_path: Path) -> None:
    """Use actual source validation for a nonexistent input file."""
    source_path = tmp_path / "missing.hwpx"

    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(FileNotFoundError):
            paragraphs.extract_hwpx_paragraphs(source_path)
    opened.assert_not_called()


@pytest.mark.parametrize("file_path", [None, 42, b"synthetic.hwpx"])
def test_invalid_path_type_is_rejected_before_open(file_path: object) -> None:
    """Let the public input API reject unsupported path types."""
    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(TypeError):
            paragraphs.extract_hwpx_paragraphs(file_path)
    opened.assert_not_called()


@pytest.mark.parametrize("suffix", [".txt", ""])
def test_unsupported_extension_is_rejected_before_open(
    tmp_path: Path, suffix: str
) -> None:
    """Leave unsupported extension validation to the existing public API."""
    source_path = tmp_path / f"synthetic{suffix}"
    source_path.write_bytes(b"synthetic source")
    before = source_path.read_bytes()

    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(ValueError, match="Supported source extensions"):
            paragraphs.extract_hwpx_paragraphs(source_path)
    opened.assert_not_called()
    assert source_path.read_bytes() == before


def test_directory_is_rejected_before_open(tmp_path: Path) -> None:
    """Reject a directory even when its name has the supported suffix."""
    source_path = tmp_path / "directory.hwpx"
    source_path.mkdir()

    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(ValueError, match="regular file"):
            paragraphs.extract_hwpx_paragraphs(source_path)
    opened.assert_not_called()


def test_empty_path_is_rejected_before_open() -> None:
    """Preserve the public validator's rejection of an empty input path."""
    with patch.object(paragraphs, "ZipFile") as opened:
        with pytest.raises(ValueError):
            paragraphs.extract_hwpx_paragraphs("")
    opened.assert_not_called()


@pytest.mark.parametrize(
    "error", [FileNotFoundError("removed"), PermissionError("denied on open")]
)
def test_source_open_error_propagates_unchanged(
    make_source: SourceFactory, error: OSError
) -> None:
    """Preserve filesystem failures occurring after successful validation."""
    source_path = make_source([("Contents/section0.xml", "<sec/>")])
    before = source_path.read_bytes()

    with patch.object(paragraphs, "ZipFile", side_effect=error) as opened:
        with pytest.raises(type(error)) as caught:
            paragraphs.extract_hwpx_paragraphs(source_path)
    assert caught.value is error
    opened.assert_called_once_with(source_path, "r")
    assert source_path.read_bytes() == before
