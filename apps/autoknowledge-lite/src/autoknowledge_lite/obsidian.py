"""Obsidian-compatible Markdown note storage."""

from __future__ import annotations

import os
import re
from pathlib import Path

from autoknowledge_lite.models import ShareRecord

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SLUG_SEPARATORS = re.compile(r"[\s-]+")


class ObsidianStoreError(RuntimeError):
    """Raised when an Obsidian note cannot be persisted."""


class ObsidianNoteStore:
    """Save generated Markdown as an atomic UTF-8 note file."""

    def __init__(self, notes_dir: Path | None = None) -> None:
        configured = os.getenv("AUTOKNOWLEDGE_VAULT_DIR")
        vault_dir = Path(configured) if configured else _default_vault_dir()
        self.notes_dir = notes_dir or vault_dir / "AutoKnowledge"

    def save(self, record: ShareRecord, markdown: str) -> Path:
        title = record.title or "untitled-knowledge"
        slug = _safe_slug(title)
        date = record.received_at.date().isoformat()
        destination = self.notes_dir / f"{date}-{slug}-{record.job_id[:8]}.md"
        temporary = destination.with_suffix(".md.tmp")
        try:
            self.notes_dir.mkdir(parents=True, exist_ok=True)
            temporary.write_text(markdown, encoding="utf-8")
            temporary.replace(destination)
        except OSError as error:
            raise ObsidianStoreError("Unable to save Obsidian note.") from error
        return destination.resolve()


def _safe_slug(title: str) -> str:
    slug = INVALID_FILENAME.sub("-", " ".join(title.split()))
    slug = SLUG_SEPARATORS.sub("-", slug).strip(" .-")
    return slug[:80] or "untitled-knowledge"


def _default_vault_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vault"
