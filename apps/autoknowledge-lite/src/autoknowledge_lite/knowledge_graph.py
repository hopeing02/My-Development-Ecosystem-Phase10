"""Deterministic metadata and links for Obsidian knowledge notes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from autoknowledge_lite.models import ShareRecord

TAG_INVALID = re.compile(r"[^\w/-]+", flags=re.UNICODE)
TAG_SEPARATOR = re.compile(r"[-_]{2,}")
HEADING = re.compile(r"^##\s+", flags=re.MULTILINE)
CONNECTIONS_SECTION = re.compile(
    r"\n## 연결\s*\n.*\Z",
    flags=re.DOTALL,
)
JOB_SUFFIX = re.compile(r"-[0-9a-f]{8}$", flags=re.IGNORECASE)

MOC_HOME = "_Home"
PRIMARY_MOCS: tuple[str, ...] = (
    "MOC - AutoKnowledge",
    "MOC - 로컬 AI와 스마트홈",
    "MOC - Android 개발",
    "MOC - 생활과 요리",
)
FOLDER_MOCS: dict[str, str] = {
    "00_Inbox": "MOC - 받은함",
    "10_Life": "MOC - 생활과 요리",
    "20_Learning": "MOC - 학습",
    "30_Interests": "MOC - 관심사",
    "40_Reference": "MOC - 참고자료",
    "90_Archive": "MOC - 보관",
    "AutoKnowledge": "MOC - AutoKnowledge",
}
MOC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "MOC - AutoKnowledge",
        ("autoknowledge", "fastapi", "mde", "워크플로"),
    ),
    (
        "MOC - 로컬 AI와 스마트홈",
        (
            "llm",
            "rag",
            "qlora",
            "스마트홈",
            "언어-모델",
            "언어모델",
            "로컬-ai",
            "온프레미스",
        ),
    ),
    (
        "MOC - Android 개발",
        ("android", "gradle", "apk", "안드로이드"),
    ),
    (
        "MOC - 생활과 요리",
        ("닭죽", "요리", "식품안전", "레시피", "recipe", "cooking"),
    ),
)
FOLDER_TYPES: dict[str, str] = {
    "00_Inbox": "capture",
    "10_Life": "life",
    "20_Learning": "learning",
    "30_Interests": "interest",
    "40_Reference": "reference",
    "90_Archive": "archive",
    "AutoKnowledge": "capture",
}
GENERIC_CONCEPT_TAGS = {
    "current",
    "git",
    "github",
    "integration-test",
    "markdown",
    "openai",
    "project",
    "현재",
    "프로젝트",
}


@dataclass(frozen=True)
class GraphMetadata:
    """Obsidian properties and links derived from one knowledge note."""

    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    note_type: str
    status: str
    reviewed: bool
    topics: tuple[str, ...]
    concepts: tuple[str, ...]


@dataclass(frozen=True)
class ParsedNote:
    """A Markdown note split into frontmatter properties and body."""

    properties: dict[str, object]
    body: str


def render_connections(
    metadata: GraphMetadata,
    *,
    canonical: str | None = None,
) -> str:
    """Render the managed Obsidian connections section."""

    lines = ["## \uc5f0\uacb0", ""]
    lines.append(
        "- \uc0c1\uc704 \uc8fc\uc81c: "
        + ", ".join(f"[[{topic}]]" for topic in metadata.topics)
    )
    if metadata.concepts:
        lines.append(
            "- \uad00\ub828 \uac1c\ub150: "
            + ", ".join(f"[[{concept}]]" for concept in metadata.concepts)
        )
    if canonical:
        lines.append(f"- \ub300\ud45c \uc815\ub9ac\ubcf8: [[{canonical}]]")
    return "\n".join(lines)


def normalize_tag(value: str) -> str:
    """Return one Obsidian-compatible, case-insensitive tag value."""

    normalized = re.sub(r"\s*/\s*", "/", value.strip().casefold())
    normalized = TAG_INVALID.sub("-", normalized)
    normalized = TAG_SEPARATOR.sub("-", normalized).strip("-_/")
    if normalized.isdecimal():
        normalized = f"topic-{normalized}"
    return normalized or "uncategorized"


def build_graph_metadata(
    *,
    title: str,
    summary: str,
    tags: list[str] | tuple[str, ...],
    folder: str,
) -> GraphMetadata:
    """Derive stable aliases, tags, type, status, topics and concept links."""

    normalized_tags = tuple(dict.fromkeys(normalize_tag(tag) for tag in tags))
    search_text = " ".join((title, summary, *normalized_tags)).casefold()
    topics = tuple(
        moc
        for moc, keywords in MOC_KEYWORDS
        if any(keyword in search_text for keyword in keywords)
    )
    if not topics:
        topics = (FOLDER_MOCS.get(folder, "MOC - 참고자료"),)

    concepts = tuple(
        _concept_name(tag)
        for tag in normalized_tags
        if tag not in GENERIC_CONCEPT_TAGS and "/" not in tag
    )[:3]
    alias = _short_alias(title, normalized_tags)
    return GraphMetadata(
        aliases=(alias,),
        tags=normalized_tags,
        note_type=FOLDER_TYPES.get(folder, "reference"),
        status="archived" if folder == "90_Archive" else "to-review",
        reviewed=False,
        topics=topics,
        concepts=concepts,
    )


def metadata_for_record(record: ShareRecord) -> GraphMetadata:
    """Build graph metadata from one analyzed share record."""

    if record.analysis is None:
        raise ValueError("Share record must be analyzed.")
    title = record.title or record.analysis.summary[:80] or "Untitled knowledge"
    return build_graph_metadata(
        title=title,
        summary=record.analysis.summary,
        tags=record.analysis.tags,
        folder=record.target_folder,
    )


def parse_note(text: str) -> ParsedNote:
    """Parse the simple YAML subset used by AutoKnowledge notes."""

    if not text.startswith("---\n"):
        return ParsedNote(properties={}, body=text)
    end = text.find("\n---\n", 4)
    if end < 0:
        return ParsedNote(properties={}, body=text)

    properties: dict[str, object] = {}
    current_list: str | None = None
    for line in text[4:end].splitlines():
        list_item = re.match(r"^\s+-\s+(.*)$", line)
        if list_item and current_list:
            value = _decode_scalar(list_item.group(1))
            existing = properties.setdefault(current_list, [])
            if isinstance(existing, list):
                existing.append(str(value))
            continue

        item = re.match(r"^([A-Za-z_][\w-]*):(?:\s*(.*))?$", line)
        if not item:
            current_list = None
            continue
        key, raw_value = item.groups()
        if not raw_value:
            properties[key] = []
            current_list = key
        else:
            properties[key] = _decode_scalar(raw_value)
            current_list = None
    return ParsedNote(properties=properties, body=text[end + 5 :])


def render_note(properties: dict[str, object], body: str) -> str:
    """Render frontmatter properties and an unchanged Markdown body."""

    preferred = (
        "title",
        "aliases",
        "source_url",
        "received_at",
        "tags",
        "type",
        "status",
        "reviewed",
        "topics",
        "canonical",
    )
    keys = [key for key in preferred if key in properties]
    keys.extend(key for key in properties if key not in keys)
    lines = ["---"]
    for key in keys:
        value = properties[key]
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {_encode_scalar(item)}" for item in value)
        else:
            lines.append(f"{key}: {_encode_scalar(value)}")
    lines.extend(("---", "", body.lstrip("\n")))
    return "\n".join(lines).rstrip() + "\n"


def organize_note(
    text: str,
    *,
    folder: str,
    canonical: str | None = None,
    duplicate_status: str | None = None,
) -> str:
    """Add managed graph properties and a final connections section."""

    parsed = parse_note(text)
    title = str(parsed.properties.get("title") or _first_heading(parsed.body))
    tags = parsed.properties.get("tags")
    tag_values = [str(tag) for tag in tags] if isinstance(tags, list) else []
    metadata = build_graph_metadata(
        title=title,
        summary=_section_text(parsed.body, "Summary"),
        tags=tag_values,
        folder=folder,
    )
    properties = dict(parsed.properties)
    properties.update(
        {
            "aliases": list(metadata.aliases),
            "tags": list(metadata.tags),
            "type": metadata.note_type,
            "status": duplicate_status or metadata.status,
            "reviewed": metadata.reviewed,
            "topics": [f"[[{topic}]]" for topic in metadata.topics],
        }
    )
    if canonical:
        properties["canonical"] = f"[[{canonical}]]"

    body = CONNECTIONS_SECTION.sub("", parsed.body).rstrip()
    connection_lines = ["## 연결", ""]
    connection_lines.append(
        "- 상위 주제: " + ", ".join(f"[[{topic}]]" for topic in metadata.topics)
    )
    if metadata.concepts:
        connection_lines.append(
            "- 관련 개념: "
            + ", ".join(f"[[{concept}]]" for concept in metadata.concepts)
        )
    if canonical:
        connection_lines.append(f"- 대표 정리본: [[{canonical}]]")
    body = f"{body}\n\n{render_connections(metadata, canonical=canonical)}"
    return render_note(properties, body)


def note_title(text: str) -> str:
    """Return a normalized title used only for duplicate candidate grouping."""

    parsed = parse_note(text)
    title = str(parsed.properties.get("title") or _first_heading(parsed.body))
    return " ".join(title.casefold().split())


def note_content_length(text: str) -> int:
    """Measure original body content without managed connection links."""

    parsed = parse_note(text)
    return len(CONNECTIONS_SECTION.sub("", parsed.body).rstrip())


def note_stem(path: Path) -> str:
    """Return the Obsidian link target for a Markdown path."""

    return path.stem


def _short_alias(title: str, tags: tuple[str, ...]) -> str:
    candidates = [
        _concept_name(tag)
        for tag in tags
        if tag not in GENERIC_CONCEPT_TAGS and "/" not in tag
    ][:3]
    if candidates:
        return " · ".join(candidates)[:80]
    clean_title = re.sub(r"[\[\]|#^]", " ", title)
    clean_title = " ".join(clean_title.split())
    return clean_title[:80] or "Untitled knowledge"


def _concept_name(tag: str) -> str:
    return tag.replace("-", " ").replace("_", " ").strip()


def _decode_scalar(value: str) -> object:
    stripped = value.strip()
    if stripped == "null":
        return None
    if stripped in {"true", "false"}:
        return stripped == "true"
    if stripped.startswith('"'):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped.strip('"')
    return stripped


def _encode_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(str(value), ensure_ascii=False)


def _first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled knowledge"


def _section_text(body: str, heading: str) -> str:
    marker = f"## {heading}"
    start = body.find(marker)
    if start < 0:
        return ""
    content_start = start + len(marker)
    match = HEADING.search(body, content_start)
    end = match.start() if match else len(body)
    return " ".join(body[content_start:end].split())
