"""Contracts for ordered, offline Markdown ebook assembly."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from apps.ebook_ai.ebook_builder import EbookBuildError, build_ebook


@pytest.fixture
def manuscript(tmp_path: Path) -> Path:
    folder = tmp_path / "원고 폴더"
    folder.mkdir()
    (folder / "뒤.MD").write_bytes(b"\xef\xbb\xbf# Second\r\n\r\nBODY_TWO\r\n")
    (folder / "앞.md").write_text(
        "# First\n\n본문 보존\n\n```python\nprint('hello')\n```\n", encoding="utf-8"
    )
    manifest = folder / "book.json"
    manifest.write_text(
        json.dumps(
            {
                "title": "가상 도서",
                "chapters": [
                    {"title": "같은 제목", "path": "뒤.MD"},
                    {"title": "같은 제목", "path": "앞.md"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8-sig",
    )
    return manifest


def test_order_body_links_and_source_preservation(manuscript: Path, tmp_path: Path):
    sources = list(manuscript.parent.iterdir())
    before = {p: hashlib.sha256(p.read_bytes()).digest() for p in sources}
    result = build_ebook(manuscript, tmp_path / "output")
    toc = result.toc_path.read_text(encoding="utf-8")
    basic = result.basic_path.read_text(encoding="utf-8")
    assert result.chapter_count == 2
    assert toc == (
        "# 목차\n\n가상 도서\n\n"
        "1. [같은 제목](basic.md#chapter-001)\n"
        "2. [같은 제목](basic.md#chapter-002)\n"
    )
    assert basic.index("BODY_TWO") < basic.index("본문 보존")
    assert "```python\nprint('hello')\n```" in basic
    for index in (1, 2):
        assert f'<a id="chapter-{index:03d}"></a>' in basic
        assert f"](#chapter-{index:03d})" in basic
    assert "\ufeff" not in basic
    assert b"\r" not in result.basic_path.read_bytes()
    assert before == {p: hashlib.sha256(p.read_bytes()).digest() for p in sources}


def test_relative_paths_and_repeatable_output(
    manuscript: Path, tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    first = build_ebook(manuscript, "one")
    second = build_ebook(manuscript, "two")
    assert first.basic_path.read_bytes() == second.basic_path.read_bytes()
    assert first.toc_path.read_bytes() == second.toc_path.read_bytes()


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"title": "book", "chapters": []},
        {"title": "book", "chapters": "file.md"},
        {"title": "book", "chapters": ["file.md"]},
        {"title": "book", "chapters": [{"title": "chapter"}]},
        {"title": "book", "chapters": [{"title": "chapter", "path": 1}]},
        {"title": "book", "chapters": [{"title": "chapter", "path": "\0"}]},
        {"title": "book\nother", "chapters": [{}]},
        {"title": "book", "chapters": [{"title": "", "path": "file.md"}]},
    ],
)
def test_invalid_manifest_does_not_create_output(tmp_path: Path, value: object):
    manifest = tmp_path / "book.json"
    manifest.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(EbookBuildError):
        build_ebook(manifest, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("content", [b"not json", b"\xff"])
def test_bad_json_and_manifest_encoding(tmp_path: Path, content: bytes):
    manifest = tmp_path / "book.json"
    manifest.write_bytes(content)
    with pytest.raises(EbookBuildError, match="JSON manifest"):
        build_ebook(manifest, tmp_path / "output")


@pytest.mark.parametrize(
    "fault", ["missing", "empty", "encoding", "directory", "extension"]
)
def test_invalid_later_manuscript_creates_no_partial_book(
    manuscript: Path, tmp_path: Path, fault: str
):
    source = manuscript.parent / "앞.md"
    if fault == "missing":
        source.unlink()
    elif fault == "empty":
        source.write_text(" \n", encoding="utf-8")
    elif fault == "encoding":
        source.write_bytes(b"\xff")
    elif fault == "directory":
        source.unlink()
        source.mkdir()
    else:
        data = json.loads(manuscript.read_text(encoding="utf-8-sig"))
        data["chapters"][1]["path"] = "file.txt"
        manuscript.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EbookBuildError):
        build_ebook(manuscript, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize("hardlink", [False, True])
def test_duplicate_sources_are_rejected(
    manuscript: Path, tmp_path: Path, hardlink: bool
):
    data = json.loads(manuscript.read_text(encoding="utf-8-sig"))
    if hardlink:
        os.link(manuscript.parent / "뒤.MD", manuscript.parent / "alias.md")
        data["chapters"][1]["path"] = "alias.md"
    else:
        data["chapters"][1]["path"] = "./뒤.MD"
    manuscript.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EbookBuildError, match="Duplicate"):
        build_ebook(manuscript, tmp_path / "output")


def test_existing_output_and_explicit_overwrite(manuscript: Path, tmp_path: Path):
    output = tmp_path / "output"
    output.mkdir()
    existing = output / "basic.md"
    existing.write_text("keep me", encoding="utf-8")
    with pytest.raises(EbookBuildError, match="exists"):
        build_ebook(manuscript, output)
    assert existing.read_text(encoding="utf-8") == "keep me"
    assert not (output / "toc.md").exists()
    build_ebook(manuscript, output, overwrite=True)
    assert "BODY_TWO" in existing.read_text(encoding="utf-8")


@pytest.mark.parametrize("hardlink", [False, True])
def test_overwrite_cannot_destroy_manuscript(manuscript: Path, hardlink: bool):
    data = json.loads(manuscript.read_text(encoding="utf-8-sig"))
    protected = manuscript.parent / "basic.md"
    if hardlink:
        os.link(manuscript.parent / "앞.md", protected)
    else:
        (manuscript.parent / "앞.md").rename(protected)
        data["chapters"][1]["path"] = "basic.md"
        manuscript.write_text(json.dumps(data), encoding="utf-8")
    before = protected.read_bytes()
    with pytest.raises(EbookBuildError, match="overwrite input"):
        build_ebook(manuscript, manuscript.parent, overwrite=True)
    assert protected.read_bytes() == before


def test_special_title_does_not_break_toc(manuscript: Path, tmp_path: Path):
    data = json.loads(manuscript.read_text(encoding="utf-8-sig"))
    data["chapters"][0]["title"] = "[예제](link) <b> & *제목*"
    manuscript.write_text(json.dumps(data), encoding="utf-8")
    result = build_ebook(manuscript, tmp_path / "output")
    toc = result.toc_path.read_text(encoding="utf-8")
    assert r"\[예제\]\(link\) &lt;b&gt; &amp; \*제목\*" in toc
    assert "<b>" not in toc


def test_output_files_cannot_alias_each_other(manuscript: Path, tmp_path: Path):
    output = tmp_path / "output"
    output.mkdir()
    toc = output / "toc.md"
    toc.write_text("preserve", encoding="utf-8")
    os.link(toc, output / "basic.md")
    with pytest.raises(EbookBuildError, match="distinct"):
        build_ebook(manuscript, output, overwrite=True)
    assert toc.read_text(encoding="utf-8") == "preserve"


def test_cli_success_and_error(manuscript: Path, tmp_path: Path):
    script = Path(__file__).resolve().parents[1] / "ebook_builder.py"
    command = [
        sys.executable,
        str(script),
        "--manifest",
        str(manuscript),
        "--output-dir",
        str(tmp_path / "cli"),
    ]
    success = subprocess.run(command, capture_output=True)
    assert success.returncode == 0, success.stderr
    assert (tmp_path / "cli" / "basic.md").exists()
    failure = subprocess.run(command, capture_output=True)
    assert failure.returncode == 1
    assert b"Ebook build failed:" in failure.stderr
    assert b"Traceback" not in failure.stderr
