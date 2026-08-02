"""Obsidian-compatible Markdown note storage."""

from __future__ import annotations

import os
import re
from pathlib import Path

from autoknowledge_lite.models import (
    ALLOWED_VAULT_FOLDERS,
    DEFAULT_VAULT_FOLDER,
    ShareRecord,
)

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SLUG_SEPARATORS = re.compile(r"[\s-]+")


class ObsidianStoreError(RuntimeError):
    """Raised when an Obsidian note cannot be persisted."""


class ObsidianNoteStore:
    """Save generated Markdown as an atomic UTF-8 note file."""

    def __init__(self, vault_dir: Path | None = None) -> None:
        configured = os.getenv("AUTOKNOWLEDGE_VAULT_DIR")
        configured_vault = Path(configured) if configured else _default_vault_dir()
        self.vault_dir = (vault_dir or configured_vault).resolve()
        self.notes_dir = self.vault_dir / DEFAULT_VAULT_FOLDER

    def save(self, record: ShareRecord, markdown: str) -> Path:
        if record.source_type and record.content_hash:
            timestamp = (record.captured_at or record.received_at).strftime(
                "%Y-%m-%d-%H%M%S"
            )
            filename = (
                f"{timestamp}-{record.source_type}-clip-"
                f"{record.content_hash[:8]}.md"
            )
            destination_dir = self._destination_dir(record.target_folder)
            destination = destination_dir / INVALID_FILENAME.sub("-", filename)
            return self._atomic_write(destination, markdown)
        title = record.title or "untitled-knowledge"
        slug = _safe_slug(title)
        date = record.received_at.date().isoformat()
        destination_dir = self._destination_dir(record.target_folder)
        destination = destination_dir / f"{date}-{slug}-{record.job_id[:8]}.md"
        return self._atomic_write(destination, markdown)

    @staticmethod
    def _atomic_write(destination: Path, markdown: str) -> Path:
        temporary = destination.with_suffix(".md.tmp")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(markdown, encoding="utf-8")
            temporary.replace(destination)
        except OSError as error:
            raise ObsidianStoreError("Unable to save Obsidian note.") from error
        return destination.resolve()

    def _destination_dir(self, folder: str) -> Path:
        if folder not in ALLOWED_VAULT_FOLDERS:
            raise ObsidianStoreError("Unsupported Vault folder.")
        destination = (self.vault_dir / folder).resolve()
        try:
            destination.relative_to(self.vault_dir)
        except ValueError as error:
            raise ObsidianStoreError(
                "Vault folder resolves outside the Vault."
            ) from error
        return destination


def _safe_slug(title: str) -> str:
    slug = INVALID_FILENAME.sub("-", " ".join(title.split()))
    slug = SLUG_SEPARATORS.sub("-", slug).strip(" .-")
    return slug[:80] or "untitled-knowledge"


def _default_vault_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "vault"
