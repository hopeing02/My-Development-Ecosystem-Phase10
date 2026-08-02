from pathlib import Path

import pytest

from mde.knowledge.parser import parse_markdown
from mde.knowledge.scanner import iter_markdown_files, scan_file


def test_parser_extracts_frontmatter_tags_aliases_and_all_link_types() -> None:
    parsed = parse_markdown(
        """---
title: 가족 일정
tags:
  - 가족
  - 일정
aliases:
  - 가족 스케줄
---
# ignored heading
#본문태그 #가족/일정
[개발 표준](../DEV/DEV-001.md)
[사이트](https://example.com)
[[가족 일정|일정 보기]]
[[가족 일정#학원]]
![[사진.png]]
```python
#not-a-tag
```
""",
        Path("일정.md"),
    )

    assert parsed.title == "가족 일정"
    assert parsed.aliases == ("가족 스케줄",)
    assert set(parsed.tags) == {"가족", "일정", "본문태그", "가족/일정"}
    assert {(link.target, link.link_type) for link in parsed.outgoing_links} == {
        ("../DEV/DEV-001.md", "internal_markdown"),
        ("https://example.com", "external_url"),
        ("가족 일정", "wiki_link"),
        ("사진.png", "attachment"),
    }
    displayed = next(
        link for link in parsed.outgoing_links if link.display_text == "일정 보기"
    )
    assert displayed.raw_target == "가족 일정|일정 보기"
    headed = next(link for link in parsed.outgoing_links if link.heading == "학원")
    assert headed.raw_target == "가족 일정#학원"


def test_parser_uses_h1_then_filename_and_continues_after_bad_frontmatter() -> None:
    assert parse_markdown("# H1 title\n", Path("file.md")).title == "H1 title"
    assert parse_markdown("plain text", Path("file.md")).title == "file"
    broken = parse_markdown("---\ntags: [broken\n---\n# Still indexed", Path("x.md"))
    assert broken.title == "Still indexed"
    assert broken.warnings == ("invalid YAML frontmatter",)


def test_scanner_recurses_and_excludes_private_tool_directories(tmp_path: Path) -> None:
    included = tmp_path / "docs" / "문서.md"
    included.parent.mkdir()
    included.write_text("# Included", encoding="utf-8")
    for directory in (".git", ".obsidian", ".mde", "node_modules", "휴지통"):
        excluded = tmp_path / directory / "hidden.md"
        excluded.parent.mkdir()
        excluded.write_text("# Hidden", encoding="utf-8")
    (tmp_path / "attachment.pdf").write_bytes(b"not indexed")

    files = iter_markdown_files(tmp_path)

    assert files == (included,)


def test_scanner_accepts_utf8_bom_and_rejects_other_encodings(tmp_path: Path) -> None:
    bom = tmp_path / "bom.md"
    bom.write_bytes("# 제목".encode("utf-8-sig"))
    scanned = scan_file(tmp_path, bom)
    assert scanned.parsed.title == "제목"

    invalid = tmp_path / "legacy.md"
    invalid.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(UnicodeDecodeError):
        scan_file(tmp_path, invalid)


def test_parser_never_extracts_frontmatter_or_code_links() -> None:
    parsed = parse_markdown(
        """---
tags: [py, 전체]
aliases: [모두, '[[가짜 메타 링크]]']
---
`[[가짜 인라인 링크]]`
```text
[[가짜 코드 링크]]
```
[[실제 링크]]
""",
        Path("링크.md"),
    )

    assert [link.target for link in parsed.outgoing_links] == ["실제 링크"]
    occurrence = parsed.outgoing_links[0]
    assert occurrence.raw_text == "[[실제 링크]]"
    assert occurrence.line == 9
    assert occurrence.column == 1
    assert occurrence.start_offset < occurrence.end_offset
    assert occurrence.occurrence_id.startswith("link-")


def test_parser_preserves_scalar_alias_as_one_value() -> None:
    parsed = parse_markdown(
        "---\naliases: 전체 연동 검증\n---\n본문\n", Path("문서.md")
    )

    assert parsed.aliases == ("전체 연동 검증",)


def test_scanner_excludes_command_backups(tmp_path: Path) -> None:
    visible = tmp_path / "visible.md"
    visible.write_text("# Visible", encoding="utf-8")
    backup = tmp_path / ".mde-backups" / "2026-07-30" / "visible.md"
    backup.parent.mkdir(parents=True)
    backup.write_text("# Backup", encoding="utf-8")

    assert iter_markdown_files(tmp_path) == (visible,)
