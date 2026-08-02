"""Data models for the MDE Knowledge Plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SOURCE_CATEGORIES = ("development", "project", "personal", "work", "shared")
SOURCE_TYPES = ("markdown", "obsidian")


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def category_defaults(category: str) -> tuple[bool, bool]:
    """Return ``(sensitive, allow_agent_access)`` defaults for a category."""

    if category not in SOURCE_CATEGORIES:
        raise ValueError(f"Unsupported source category: {category}")
    sensitive = category in {"personal", "work"}
    return sensitive, not sensitive


def capture_write_default(category: str) -> bool:
    """Return whether capture applications may write to a category by default."""

    if category not in SOURCE_CATEGORIES:
        raise ValueError(f"Unsupported source category: {category}")
    return category in {"development", "project", "personal"}


def viewer_edit_defaults(category: str) -> tuple[bool, bool]:
    """Return ``(editable_in_viewer, allow_link_rewrite)`` defaults."""

    if category not in SOURCE_CATEGORIES:
        raise ValueError(f"Unsupported source category: {category}")
    editable = category in {"development", "project", "personal"}
    return editable, editable


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    name: str
    path: Path
    category: str
    source_type: str = "markdown"
    enabled: bool = True
    sensitive: bool = False
    allow_agent_access: bool = True
    writable_by_capture_app: bool = True
    read_only: bool = False
    editable_in_viewer: bool = True
    allow_link_rewrite: bool = True
    allow_document_create: bool = False
    allow_as_shared_link_target: bool = False
    created_at: datetime = field(default_factory=utc_now)
    last_scanned_at: datetime | None = None


@dataclass(frozen=True)
class ExtractedLink:
    target: str
    link_type: str
    display_text: str | None = None
    raw_target: str | None = None
    heading: str | None = None
    occurrence_id: str = ""
    raw_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    line: int = 1
    column: int = 1
    context_preview: str = ""
    resolution_status: str = "unresolved"


@dataclass(frozen=True)
class ParsedMarkdown:
    title: str
    content: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    outgoing_links: tuple[ExtractedLink, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeDocument:
    id: str
    source_id: str
    relative_path: str
    absolute_path: Path
    title: str
    content: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    outgoing_links: tuple[ExtractedLink, ...]
    modified_at: datetime
    indexed_at: datetime
    content_hash: str
    file_size: int


@dataclass(frozen=True)
class SearchResult:
    source_id: str
    source_name: str
    category: str
    sensitive: bool
    document_id: str
    title: str
    relative_path: str
    snippet: str


@dataclass(frozen=True)
class ScanError:
    relative_path: str
    message: str


@dataclass(frozen=True)
class ScanResult:
    source: KnowledgeSource
    added_count: int
    updated_count: int
    deleted_count: int
    unchanged_count: int
    errors: tuple[ScanError, ...]

    @property
    def error_count(self) -> int:
        return len(self.errors)


@dataclass(frozen=True)
class IndexFileResult:
    source: KnowledgeSource
    document_id: str
    relative_path: str
    indexed: bool
    status: str
    title: str
    tag_count: int
    link_count: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class GraphDocumentRecord:
    id: str
    source_id: str
    title: str
    relative_path: str
    category: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    modified_at: datetime
    indexed_at: datetime
    content: str
    content_hash: str


@dataclass(frozen=True)
class GraphLinkRecord:
    id: int
    source_document_id: str
    target_document_id: str | None
    target: str
    link_type: str
    resolution_status: str
    display_text: str | None = None
    raw_target: str = ""
    occurrence_id: str = ""
    raw_text: str = ""
    start_offset: int = 0
    end_offset: int = 0
    line: int = 1
    column: int = 1
    context_preview: str = ""


@dataclass(frozen=True)
class KnowledgeGraphNode:
    id: str
    source_id: str
    title: str
    relative_path: str
    category: str
    tags: tuple[str, ...]
    incoming_count: int
    outgoing_count: int
    broken_outgoing_count: int
    is_orphan: bool
    modified_at: datetime


@dataclass(frozen=True)
class KnowledgeGraphEdge:
    id: str
    source: str
    target: str
    link_type: str
    display_text: str | None = None


@dataclass(frozen=True)
class KnowledgeGraphBrokenLink:
    id: str
    source_document_id: str
    target: str
    link_type: str
    resolution_status: str


@dataclass(frozen=True)
class KnowledgeGraph:
    source: KnowledgeSource
    nodes: tuple[KnowledgeGraphNode, ...]
    edges: tuple[KnowledgeGraphEdge, ...]
    broken_links: tuple[KnowledgeGraphBrokenLink, ...]
    total_document_count: int
    returned_document_count: int
    truncated: bool


@dataclass(frozen=True)
class KnowledgeDocumentReference:
    document_id: str
    source_id: str
    title: str


@dataclass(frozen=True)
class KnowledgeTagCount:
    name: str
    document_count: int


@dataclass(frozen=True)
class KnowledgeDocumentDetail:
    id: str
    source_id: str
    title: str
    relative_path: str
    category: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    modified_at: datetime
    indexed_at: datetime
    preview: str
    outgoing_documents: tuple[KnowledgeDocumentReference, ...]
    incoming_documents: tuple[KnowledgeDocumentReference, ...]
    unresolved_links: tuple[str, ...]
    ambiguous_links: tuple[str, ...]
    body: str = ""
    raw_content: str = ""
    frontmatter: dict[str, object] = field(default_factory=dict)
    content_hash: str = ""
    editable: bool = False
    unresolved_occurrences: tuple[ExtractedLink, ...] = ()
