"""Small Markdown and Obsidian metadata parser."""

from __future__ import annotations

import re
import hashlib
from pathlib import Path
from typing import Any

import yaml

from mde.knowledge.models import ExtractedLink, ParsedMarkdown

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_FENCED_CODE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_INLINE_CODE = re.compile(r"(?<!`)`(?!`)(?:\\`|[^`])*?`", re.DOTALL)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_BODY_TAG = re.compile(r"(?<!\S)#(?!#)([^\s#.,;:!?()[\]{}<>]+)")
_ATTACHMENT = re.compile(r"!\[\[([^\]]+)\]\]")
_WIKI = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
_MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")


def _string_list(value: Any, *, split_scalar: bool = True) -> tuple[str, ...]:
    if isinstance(value, str):
        values = re.split(r"[,\s]+", value.strip()) if split_scalar else [value.strip()]
    elif isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        return ()
    return tuple(dict.fromkeys(item.lstrip("#") for item in values if item))


def _wiki_parts(raw: str) -> tuple[str, str | None, str | None]:
    target, separator, display_text = raw.partition("|")
    normalized, heading_separator, heading = target.partition("#")
    return (
        normalized.strip(),
        heading.strip() if heading_separator else None,
        display_text.strip() if separator else None,
    )


def split_frontmatter(content: str) -> tuple[dict[str, Any], str, int, tuple[str, ...]]:
    """Return parsed frontmatter, body, body offset, and safe parser warnings."""

    metadata: dict[str, Any] = {}
    warnings: list[str] = []
    match = _FRONTMATTER.match(content)
    if not match:
        return metadata, content, 0, ()
    try:
        loaded = yaml.safe_load(match.group(1))
        if isinstance(loaded, dict):
            metadata = loaded
        elif loaded is not None:
            warnings.append("frontmatter root is not a mapping")
    except yaml.YAMLError:
        warnings.append("invalid YAML frontmatter")
    return metadata, content[match.end() :], match.end(), tuple(warnings)


def _mask_ignored(text: str) -> str:
    """Blank code regions without changing offsets used by link occurrences."""

    masked = list(text)
    for pattern in (_FENCED_CODE, _INLINE_CODE):
        current = "".join(masked)
        for match in pattern.finditer(current):
            masked[match.start() : match.end()] = " " * (match.end() - match.start())
    return "".join(masked)


def _occurrence(
    content: str,
    match: re.Match[str],
    *,
    body_offset: int,
    target: str,
    link_type: str,
    display_text: str | None,
    raw_target: str,
    heading: str | None,
) -> ExtractedLink:
    start = body_offset + match.start()
    end = body_offset + match.end()
    raw_text = content[start:end]
    line = content.count("\n", 0, start) + 1
    previous_newline = content.rfind("\n", 0, start)
    column = start - previous_newline
    context_start = max(0, content.rfind("\n", 0, start) + 1)
    next_newline = content.find("\n", end)
    context_end = len(content) if next_newline < 0 else next_newline
    identity = f"{start}:{end}:{raw_text}".encode("utf-8")
    return ExtractedLink(
        target=target,
        link_type=link_type,
        display_text=display_text,
        raw_target=raw_target,
        heading=heading,
        occurrence_id=f"link-{hashlib.sha256(identity).hexdigest()[:16]}",
        raw_text=raw_text,
        start_offset=start,
        end_offset=end,
        line=line,
        column=column,
        context_preview=content[context_start:context_end].strip()[:240],
    )


def parse_markdown(text: str, path: Path) -> ParsedMarkdown:
    """Extract searchable metadata without modifying the source text."""

    content = text.lstrip("\ufeff")
    metadata, body, body_offset, parser_warnings = split_frontmatter(content)
    warnings = list(parser_warnings)

    title_value = metadata.get("title")
    if isinstance(title_value, str) and title_value.strip():
        title = title_value.strip()
    else:
        h1 = _H1.search(body)
        title = h1.group(1).strip() if h1 else path.stem

    clean_body = _mask_ignored(body)
    tags = list(_string_list(metadata.get("tags")))
    tags.extend(match.group(1) for match in _BODY_TAG.finditer(clean_body))
    unique_tags = tuple(dict.fromkeys(tag for tag in tags if tag))
    aliases = _string_list(metadata.get("aliases"), split_scalar=False)

    links: list[ExtractedLink] = []
    for attachment in _ATTACHMENT.finditer(clean_body):
        raw_target = attachment.group(1).strip()
        target, heading, display_text = _wiki_parts(raw_target)
        links.append(_occurrence(content, attachment, body_offset=body_offset, target=target, link_type="attachment", display_text=display_text, raw_target=raw_target, heading=heading))
    for wiki in _WIKI.finditer(clean_body):
        raw_target = wiki.group(1).strip()
        target, heading, display_text = _wiki_parts(raw_target)
        if target:
            links.append(_occurrence(content, wiki, body_offset=body_offset, target=target, link_type="wiki_link", display_text=display_text, raw_target=raw_target, heading=heading))
    for markdown in _MARKDOWN_LINK.finditer(clean_body):
        display_text = markdown.group(1).strip() or None
        raw_target = markdown.group(2).strip().split(maxsplit=1)[0].strip("<>")
        link_type = (
            "external_url"
            if raw_target.lower().startswith(("http://", "https://"))
            else "internal_markdown"
        )
        target, separator, heading = raw_target.partition("#")
        links.append(_occurrence(content, markdown, body_offset=body_offset, target=target, link_type=link_type, display_text=display_text, raw_target=raw_target, heading=heading.strip() if separator else None))

    return ParsedMarkdown(
        title=title,
        content=content,
        tags=unique_tags,
        aliases=aliases,
        outgoing_links=tuple(dict.fromkeys(links)),
        warnings=tuple(warnings),
    )
