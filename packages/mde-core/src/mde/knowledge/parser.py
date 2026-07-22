"""Small Markdown and Obsidian metadata parser."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from mde.knowledge.models import ExtractedLink, ParsedMarkdown

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
_FENCED_CODE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_BODY_TAG = re.compile(r"(?<!\S)#(?!#)([^\s#.,;:!?()[\]{}<>]+)")
_ATTACHMENT = re.compile(r"!\[\[([^\]]+)\]\]")
_WIKI = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
_MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def _string_list(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        values = re.split(r"[,\s]+", value.strip())
    elif isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        return ()
    return tuple(dict.fromkeys(item.lstrip("#") for item in values if item))


def _wiki_target(raw: str) -> str:
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


def parse_markdown(text: str, path: Path) -> ParsedMarkdown:
    """Extract searchable metadata without modifying the source text."""

    content = text.lstrip("\ufeff")
    body = content
    metadata: dict[str, Any] = {}
    warnings: list[str] = []
    match = _FRONTMATTER.match(content)
    if match:
        body = content[match.end() :]
        try:
            loaded = yaml.safe_load(match.group(1))
            if isinstance(loaded, dict):
                metadata = loaded
            elif loaded is not None:
                warnings.append("frontmatter root is not a mapping")
        except yaml.YAMLError:
            warnings.append("invalid YAML frontmatter")

    title_value = metadata.get("title")
    if isinstance(title_value, str) and title_value.strip():
        title = title_value.strip()
    else:
        h1 = _H1.search(body)
        title = h1.group(1).strip() if h1 else path.stem

    clean_body = _FENCED_CODE.sub("", body)
    tags = list(_string_list(metadata.get("tags")))
    tags.extend(match.group(1) for match in _BODY_TAG.finditer(clean_body))
    unique_tags = tuple(dict.fromkeys(tag for tag in tags if tag))
    aliases = _string_list(metadata.get("aliases"))

    links: list[ExtractedLink] = []
    for attachment in _ATTACHMENT.finditer(clean_body):
        links.append(ExtractedLink(attachment.group(1).strip(), "attachment"))
    for wiki in _WIKI.finditer(clean_body):
        target = _wiki_target(wiki.group(1))
        if target:
            links.append(ExtractedLink(target, "wiki_link"))
    for markdown in _MARKDOWN_LINK.finditer(clean_body):
        target = markdown.group(1).strip().split(maxsplit=1)[0].strip("<>")
        link_type = (
            "external_url"
            if target.lower().startswith(("http://", "https://"))
            else "internal_markdown"
        )
        links.append(ExtractedLink(target, link_type))

    return ParsedMarkdown(
        title=title,
        content=content,
        tags=unique_tags,
        aliases=aliases,
        outgoing_links=tuple(dict.fromkeys(links)),
        warnings=tuple(warnings),
    )
