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
                "<s:tbl><s:tc><s:p><s:t>셀1</s:t></s:p></s:tc>"
                "<s:tc><s:p><s:t>셀2</s:t></s:p></s:tc></s:tbl>"
                "<s:t>꼬리</s:t></s:p></s:sec>",
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
    path = make_hwpx([(0, "<sec><p><t>A</t><t> B</t></p><p/><p><t>C</t></p></sec>")])
    assert extract_hwpx_paragraphs(path) == ["A B", "", "C"]
