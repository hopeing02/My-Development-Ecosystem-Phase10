"""Application service for local Knowledge Plugin operations."""

from __future__ import annotations

from pathlib import Path

from mde.knowledge.audit import KnowledgeAuditLogger
from mde.knowledge.errors import KnowledgeContractError, SourceValidationError
from mde.knowledge.graph import KnowledgeGraphService
from mde.knowledge.models import (
    IndexFileResult,
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
        self.graphs = KnowledgeGraphService(self.registry, self.repository)
        for source in self.registry.list():
            self.repository.upsert_source(source)
        self.repository.resolve_all_links()

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
        writable_by_capture_app: bool | None = None,
        read_only: bool | None = None,
        editable_in_viewer: bool | None = None,
        allow_link_rewrite: bool | None = None,
        allow_as_shared_link_target: bool | None = None,
        confirm_sensitive_access: bool = False,
        confirm_sensitive_write: bool = False,
    ) -> KnowledgeSource:
        source = self.registry.update(
            name_or_id,
            enabled=enabled,
            allow_agent_access=allow_agent_access,
            writable_by_capture_app=writable_by_capture_app,
            read_only=read_only,
            editable_in_viewer=editable_in_viewer,
            allow_link_rewrite=allow_link_rewrite,
            allow_as_shared_link_target=allow_as_shared_link_target,
            confirm_sensitive_access=confirm_sensitive_access,
            confirm_sensitive_write=confirm_sensitive_write,
        )
        self.repository.upsert_source(source)
        changes = {
            key: value
            for key, value in {
                "enabled": enabled,
                "allow_agent_access": allow_agent_access,
                "writable_by_capture_app": writable_by_capture_app,
                "read_only": read_only,
                "editable_in_viewer": editable_in_viewer,
                "allow_link_rewrite": allow_link_rewrite,
                "allow_as_shared_link_target": allow_as_shared_link_target,
            }.items()
            if value is not None
        }
        self.audit.source_updated(source, changes)
        self.repository.resolve_all_links()
        return source

    def index_file(
        self,
        source: str,
        relative_path: str,
        *,
        require_capture_write: bool = True,
    ) -> IndexFileResult:
        """Safely index one Markdown file already stored inside a source."""

        selected = self.registry.get(source)
        if not selected.enabled:
            raise KnowledgeContractError(
                "SOURCE_DISABLED", "Knowledge source is disabled.", source=source
            )
        if require_capture_write and not selected.writable_by_capture_app:
            raise KnowledgeContractError(
                "SOURCE_NOT_WRITABLE",
                "Knowledge source does not allow capture application writes.",
                source=source,
            )
        requested = Path(relative_path)
        if not relative_path.strip() or requested.is_absolute():
            raise KnowledgeContractError(
                "INVALID_RELATIVE_PATH",
                "A source-relative Markdown path is required.",
                path=relative_path,
            )
        try:
            root = selected.path.resolve(strict=True)
        except OSError as error:
            raise KnowledgeContractError(
                "SOURCE_PATH_NOT_FOUND",
                "Knowledge source path was not found.",
                source=source,
            ) from error
        try:
            target = (root / requested).resolve(strict=True)
        except FileNotFoundError as error:
            raise KnowledgeContractError(
                "FILE_NOT_FOUND", "Markdown file was not found.", path=relative_path
            ) from error
        try:
            target.relative_to(root)
        except ValueError as error:
            raise KnowledgeContractError(
                "PATH_OUTSIDE_SOURCE",
                "The requested file is outside the registered knowledge source.",
                source=source,
                path=relative_path,
            ) from error
        if not target.is_file():
            raise KnowledgeContractError(
                "FILE_NOT_FOUND", "Markdown file was not found.", path=relative_path
            )
        if target.suffix.casefold() != ".md":
            raise KnowledgeContractError(
                "FILE_NOT_MARKDOWN",
                "Only Markdown files can be indexed.",
                path=relative_path,
            )

        normalized_path = target.relative_to(root).as_posix()
        try:
            scanned = scan_file(root, target)
        except UnicodeError as error:
            raise KnowledgeContractError(
                "ENCODING_ERROR", "Markdown file must be UTF-8.", path=normalized_path
            ) from error
        except OSError as error:
            raise KnowledgeContractError(
                "FILE_READ_ERROR", "Unable to read Markdown file.", path=normalized_path
            ) from error
        previous = self.repository.document_state(selected.id).get(normalized_path)
        changed = previous is None or previous[0] != scanned.content_hash
        status = "added" if previous is None else "updated"
        document_id = f"{selected.id}::{normalized_path}"
        if changed:
            self.repository.save_document(
                KnowledgeDocument(
                    id=document_id,
                    source_id=selected.id,
                    relative_path=normalized_path,
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
            )
        else:
            status = "unchanged"
        self.repository.resolve_all_links()
        return IndexFileResult(
            source=selected,
            document_id=document_id,
            relative_path=normalized_path,
            indexed=changed,
            status=status,
            title=scanned.parsed.title,
            tag_count=len(scanned.parsed.tags),
            link_count=len(scanned.parsed.outgoing_links),
            warnings=scanned.parsed.warnings,
        )

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
        self.repository.resolve_all_links()
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
