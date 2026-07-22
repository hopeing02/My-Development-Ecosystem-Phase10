"""Application service for local Knowledge Plugin operations."""

from __future__ import annotations

from pathlib import Path

from mde.knowledge.audit import KnowledgeAuditLogger
from mde.knowledge.errors import SourceValidationError
from mde.knowledge.models import (
    KnowledgeDocument,
    KnowledgeSource,
    ScanError,
    ScanResult,
    SearchResult,
    utc_now,
)
from mde.knowledge.paths import knowledge_database_path, source_registry_path
from mde.knowledge.registry import SourceRegistry
from mde.knowledge.repository import KnowledgeRepository
from mde.knowledge.scanner import iter_markdown_files, scan_file


class KnowledgeService:
    """Coordinate the registry, read-only scanner, and SQLite index."""

    def __init__(
        self,
        registry_path: Path | None = None,
        database_path: Path | None = None,
        *,
        force_like_search: bool = False,
        audit_log_dir: Path | None = None,
    ) -> None:
        resolved_registry_path = registry_path or source_registry_path()
        resolved_database_path = database_path or knowledge_database_path()
        self.registry = SourceRegistry(resolved_registry_path)
        self.repository = KnowledgeRepository(
            resolved_database_path,
            force_like_search=force_like_search,
        )
        self.audit = KnowledgeAuditLogger(
            audit_log_dir or resolved_database_path.parent / "logs"
        )
        for source in self.registry.list():
            self.repository.upsert_source(source)

    def add_source(
        self,
        path: Path,
        *,
        name: str,
        category: str,
        source_type: str = "markdown",
    ) -> KnowledgeSource:
        source = self.registry.add(
            path, name=name, category=category, source_type=source_type
        )
        self.repository.upsert_source(source)
        self.audit.source_added(source)
        return source

    def list_sources(self) -> tuple[KnowledgeSource, ...]:
        return self.registry.list()

    def show_source(self, name_or_id: str) -> tuple[KnowledgeSource, int]:
        source = self.registry.get(name_or_id)
        return source, self.repository.document_count(source.id)

    def update_source(
        self,
        name_or_id: str,
        *,
        enabled: bool | None = None,
        allow_agent_access: bool | None = None,
        confirm_sensitive_access: bool = False,
    ) -> KnowledgeSource:
        source = self.registry.update(
            name_or_id,
            enabled=enabled,
            allow_agent_access=allow_agent_access,
            confirm_sensitive_access=confirm_sensitive_access,
        )
        self.repository.upsert_source(source)
        changes = {
            key: value
            for key, value in {
                "enabled": enabled,
                "allow_agent_access": allow_agent_access,
            }.items()
            if value is not None
        }
        self.audit.source_updated(source, changes)
        return source

    def remove_source(self, name_or_id: str) -> KnowledgeSource:
        source = self.registry.get(name_or_id)
        self.repository.remove_source(source.id)
        removed = self.registry.remove(name_or_id)
        self.audit.source_removed(removed)
        return removed

    def scan_source(self, name_or_id: str) -> ScanResult:
        source = self.registry.get(name_or_id)
        if not source.enabled:
            raise SourceValidationError(f"Knowledge source is disabled: {source.name}")
        self.audit.scan_started(source)
        try:
            result = self._scan_source(source)
        except Exception as error:
            self.audit.scan_failed(source, error)
            raise
        self.audit.scan_completed(result)
        return result

    def _scan_source(self, source: KnowledgeSource) -> ScanResult:
        started_at = utc_now()
        previous = self.repository.document_state(source.id)
        discovered: set[str] = set()
        added = 0
        updated = 0
        unchanged = 0
        errors: list[ScanError] = []

        for path in iter_markdown_files(source.path):
            relative_path = path.relative_to(source.path).as_posix()
            discovered.add(relative_path)
            try:
                scanned = scan_file(source.path, path)
            except (OSError, UnicodeError) as error:
                errors.append(ScanError(relative_path, self._safe_file_error(error)))
                continue
            current = previous.get(scanned.relative_path)
            if current and current[0] == scanned.content_hash:
                unchanged += 1
                continue
            document = KnowledgeDocument(
                id=f"{source.id}::{scanned.relative_path}",
                source_id=source.id,
                relative_path=scanned.relative_path,
                absolute_path=scanned.absolute_path,
                title=scanned.parsed.title,
                content=scanned.parsed.content,
                tags=scanned.parsed.tags,
                aliases=scanned.parsed.aliases,
                outgoing_links=scanned.parsed.outgoing_links,
                modified_at=scanned.modified_at,
                indexed_at=utc_now(),
                content_hash=scanned.content_hash,
                file_size=scanned.file_size,
            )
            self.repository.save_document(document)
            if current:
                updated += 1
            else:
                added += 1
            errors.extend(
                ScanError(scanned.relative_path, warning)
                for warning in scanned.parsed.warnings
            )

        deleted_paths = set(previous) - discovered
        deleted = self.repository.delete_documents(source.id, deleted_paths)
        finished_at = utc_now()
        updated_source = self.registry.update(source.id, last_scanned_at=finished_at)
        self.repository.upsert_source(updated_source)
        result = ScanResult(
            source=updated_source,
            added_count=added,
            updated_count=updated,
            deleted_count=deleted,
            unchanged_count=unchanged,
            errors=tuple(errors),
        )
        self.repository.record_scan(result, started_at, finished_at)
        return result

    def scan_selected(
        self,
        *,
        all_sources: bool = False,
        category: str | None = None,
        include_sensitive: bool = False,
    ) -> tuple[ScanResult, ...]:
        if not all_sources and category is None:
            raise SourceValidationError("Use a source name, --all, or --category.")
        selected = tuple(
            source
            for source in self.registry.list()
            if source.enabled
            and (category is None or source.category == category)
            and (include_sensitive or not source.sensitive)
        )
        return tuple(self.scan_source(source.id) for source in selected)

    def search(
        self,
        query: str | None = None,
        *,
        source: str | None = None,
        category: str | None = None,
        all_sources: bool = False,
        include_sensitive: bool = False,
        tag: str | None = None,
        limit: int = 20,
    ) -> tuple[SearchResult, ...]:
        if not query and not tag:
            raise SourceValidationError("A search query or --tag is required.")
        sources = self._select_sources(
            source=source,
            category=category,
            all_sources=all_sources,
            include_sensitive=include_sensitive,
        )
        return self.repository.search(
            source_ids=tuple(item.id for item in sources),
            query=query,
            tag=tag,
            limit=limit,
        )

    def backlinks(
        self, document: str, *, source: str, limit: int = 100
    ) -> tuple[SearchResult, ...]:
        selected = self.registry.get(source)
        if not selected.enabled:
            raise SourceValidationError(
                f"Knowledge source is disabled: {selected.name}"
            )
        return self.repository.backlinks(
            source_id=selected.id, document=document, limit=limit
        )

    def search_for_agent(
        self,
        query: str,
        source_ids: list[str] | None = None,
        *,
        limit: int = 20,
    ) -> tuple[SearchResult, ...]:
        allowed = tuple(
            source
            for source in self.registry.list()
            if source.enabled
            and source.allow_agent_access
            and not source.sensitive
            and (source_ids is None or source.id in source_ids)
        )
        return self.repository.search(
            source_ids=tuple(source.id for source in allowed),
            query=query,
            limit=limit,
        )

    def _select_sources(
        self,
        *,
        source: str | None,
        category: str | None,
        all_sources: bool,
        include_sensitive: bool,
    ) -> tuple[KnowledgeSource, ...]:
        if source:
            selected = self.registry.get(source)
            return (selected,) if selected.enabled else ()
        return tuple(
            item
            for item in self.registry.list()
            if item.enabled
            and (category is None or item.category == category)
            and (include_sensitive or not item.sensitive)
            and (all_sources or item.category in {"development", "project", "shared"})
        )

    @staticmethod
    def _safe_file_error(error: BaseException) -> str:
        if isinstance(error, UnicodeError):
            return "unable to decode as UTF-8"
        return f"unable to read file: {type(error).__name__}"
