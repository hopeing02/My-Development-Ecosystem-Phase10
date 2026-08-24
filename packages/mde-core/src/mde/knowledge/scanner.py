"""Read-only recursive Markdown source scanner."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from mde.knowledge.models import ParsedMarkdown
from mde.knowledge.parser import parse_markdown

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".obsidian",
        ".mde",
        ".mde-backups",
        ".mde-trash",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "temp",
        "tmp",
        "trash",
        "휴지통",
    }
)


@dataclass(frozen=True)
class ScannedFile:
    relative_path: str
    absolute_path: Path
    modified_at: datetime
    file_size: int
    content_hash: str
    parsed: ParsedMarkdown


def iter_markdown_files(root: Path) -> tuple[Path, ...]:
    """Return source Markdown files without traversing excluded content."""

    files: list[Path] = []
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part.casefold() in EXCLUDED_DIRECTORIES for part in relative.parts[:-1]):
            continue
        if path.is_file():
            if path.name.endswith(".mde-tmp"):
                continue
            files.append(path)
    return tuple(sorted(files, key=lambda item: item.as_posix().casefold()))


def read_markdown(path: Path) -> str:
    """Read UTF-8 Markdown, accepting an optional UTF-8 BOM."""

    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8-sig")


def scan_file(root: Path, path: Path) -> ScannedFile:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8-sig")
    stat = path.stat()
    return ScannedFile(
        relative_path=path.relative_to(root).as_posix(),
        absolute_path=path.resolve(),
        modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
        file_size=stat.st_size,
        content_hash=hashlib.sha256(data).hexdigest(),
        parsed=parse_markdown(text, path),
    )
