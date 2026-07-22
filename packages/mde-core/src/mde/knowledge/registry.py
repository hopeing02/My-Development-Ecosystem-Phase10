"""JSON-backed registry for user-local knowledge sources."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from mde.knowledge.errors import SourceNotFoundError, SourceValidationError
from mde.knowledge.models import (
    SOURCE_CATEGORIES,
    SOURCE_TYPES,
    KnowledgeSource,
    category_defaults,
)


def normalize_source_path(path: Path) -> Path:
    """Resolve a source path while preserving Windows and Unicode semantics."""

    return path.expanduser().resolve(strict=True)


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


class SourceRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list(self) -> tuple[KnowledgeSource, ...]:
        return tuple(sorted(self._load(), key=lambda item: item.id))

    def get(self, name_or_id: str) -> KnowledgeSource:
        for source in self._load():
            if source.id == name_or_id or source.name == name_or_id:
                return source
        raise SourceNotFoundError(f"Knowledge source not found: {name_or_id}")

    def add(
        self,
        source_path: Path,
        *,
        name: str,
        category: str,
        source_type: str = "markdown",
    ) -> KnowledgeSource:
        clean_name = name.strip()
        if not clean_name:
            raise SourceValidationError("Source name must not be empty.")
        if category not in SOURCE_CATEGORIES:
            raise SourceValidationError(f"Unsupported source category: {category}")
        if source_type not in SOURCE_TYPES:
            raise SourceValidationError(f"Unsupported source type: {source_type}")
        try:
            normalized = normalize_source_path(source_path)
        except (OSError, RuntimeError) as error:
            raise SourceValidationError(
                f"Source path does not exist: {source_path}"
            ) from error
        if not normalized.is_dir():
            raise SourceValidationError(f"Source path is not a directory: {normalized}")
        if not os.access(normalized, os.R_OK):
            raise SourceValidationError(f"Source path is not readable: {normalized}")

        sources = list(self._load())
        if any(source.name.casefold() == clean_name.casefold() for source in sources):
            raise SourceValidationError(f"Source name already exists: {clean_name}")
        normalized_key = _path_key(normalized)
        if any(_path_key(source.path) == normalized_key for source in sources):
            raise SourceValidationError(f"Source path already exists: {normalized}")

        sensitive, allow_agent_access = category_defaults(category)
        source = KnowledgeSource(
            id=self._next_id(sources),
            name=clean_name,
            path=normalized,
            category=category,
            source_type=source_type,
            sensitive=sensitive,
            allow_agent_access=allow_agent_access,
        )
        self._save([*sources, source])
        return source

    def update(
        self,
        name_or_id: str,
        *,
        enabled: bool | None = None,
        allow_agent_access: bool | None = None,
        confirm_sensitive_access: bool = False,
        last_scanned_at: datetime | None = None,
    ) -> KnowledgeSource:
        sources = list(self._load())
        current = self.get(name_or_id)
        if (
            current.sensitive
            and allow_agent_access is True
            and not current.allow_agent_access
            and not confirm_sensitive_access
        ):
            raise SourceValidationError(
                "Enabling agent access for a sensitive source requires "
                "--confirm-sensitive-access."
            )
        updated = replace(
            current,
            enabled=current.enabled if enabled is None else enabled,
            allow_agent_access=(
                current.allow_agent_access
                if allow_agent_access is None
                else allow_agent_access
            ),
            last_scanned_at=(
                current.last_scanned_at if last_scanned_at is None else last_scanned_at
            ),
        )
        self._save([updated if item.id == current.id else item for item in sources])
        return updated

    def remove(self, name_or_id: str) -> KnowledgeSource:
        source = self.get(name_or_id)
        self._save([item for item in self._load() if item.id != source.id])
        return source

    def _load(self) -> list[KnowledgeSource]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SourceValidationError(
                f"Unable to read source registry: {self.path}"
            ) from error
        if not isinstance(data, list):
            raise SourceValidationError("Source registry root must be a list.")
        return [self._deserialize(item) for item in data]

    def _save(self, sources: list[KnowledgeSource]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._serialize(source) for source in sources]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _next_id(sources: list[KnowledgeSource]) -> str:
        numbers = [int(item.id.removeprefix("ks-")) for item in sources]
        return f"ks-{max(numbers, default=0) + 1:03d}"

    @staticmethod
    def _serialize(source: KnowledgeSource) -> dict[str, Any]:
        return {
            "id": source.id,
            "name": source.name,
            "path": str(source.path),
            "category": source.category,
            "source_type": source.source_type,
            "enabled": source.enabled,
            "sensitive": source.sensitive,
            "allow_agent_access": source.allow_agent_access,
            "created_at": source.created_at.isoformat(),
            "last_scanned_at": (
                source.last_scanned_at.isoformat() if source.last_scanned_at else None
            ),
        }

    @staticmethod
    def _deserialize(data: Any) -> KnowledgeSource:
        if not isinstance(data, dict):
            raise SourceValidationError("Invalid source registry entry.")
        try:
            return KnowledgeSource(
                id=str(data["id"]),
                name=str(data["name"]),
                path=Path(str(data["path"])),
                category=str(data["category"]),
                source_type=str(data["source_type"]),
                enabled=bool(data["enabled"]),
                sensitive=bool(data["sensitive"]),
                allow_agent_access=bool(data["allow_agent_access"]),
                created_at=datetime.fromisoformat(str(data["created_at"])),
                last_scanned_at=(
                    datetime.fromisoformat(str(data["last_scanned_at"]))
                    if data.get("last_scanned_at")
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SourceValidationError("Invalid source registry entry.") from error
