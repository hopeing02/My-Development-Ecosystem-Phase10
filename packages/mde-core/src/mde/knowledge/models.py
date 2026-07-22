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
    created_at: datetime = field(default_factory=utc_now)
    last_scanned_at: datetime | None = None


@dataclass(frozen=True)
class ExtractedLink:
    target: str
    link_type: str


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
