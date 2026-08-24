"""Source-scoped SQLite repository for the local knowledge index."""

from __future__ import annotations

import json
import posixpath
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from mde.knowledge.errors import KnowledgeDatabaseError
from mde.knowledge.models import (
    GraphDocumentRecord,
    GraphLinkRecord,
    KnowledgeDocument,
    KnowledgeSource,
    ScanResult,
    SearchResult,
)


class KnowledgeRepository:
    def __init__(self, path: Path, *, force_like_search: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fts_enabled = False
        try:
            with self._connect() as connection:
                self._create_schema(connection, force_like_search=force_like_search)
        except sqlite3.Error as error:
            raise KnowledgeDatabaseError(
                f"Unable to initialize knowledge database: {self.path}"
            ) from error

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _create_schema(
        self, connection: sqlite3.Connection, *, force_like_search: bool
    ) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS knowledge_sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                source_type TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                sensitive INTEGER NOT NULL,
                allow_agent_access INTEGER NOT NULL,
                allow_as_shared_link_target INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_scanned_at TEXT
            );
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                absolute_path TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                aliases TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                UNIQUE(source_id, relative_path),
                FOREIGN KEY(source_id) REFERENCES knowledge_sources(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS knowledge_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                UNIQUE(source_id, document_id, tag),
                FOREIGN KEY(source_id) REFERENCES knowledge_sources(id) ON DELETE CASCADE,
                FOREIGN KEY(document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS knowledge_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                source_document_id TEXT NOT NULL,
                target TEXT NOT NULL,
                raw_target TEXT NOT NULL DEFAULT '',
                normalized_target TEXT NOT NULL DEFAULT '',
                link_type TEXT NOT NULL,
                heading TEXT,
                display_text TEXT,
                occurrence_id TEXT NOT NULL DEFAULT '',
                raw_text TEXT NOT NULL DEFAULT '',
                start_offset INTEGER NOT NULL DEFAULT 0,
                end_offset INTEGER NOT NULL DEFAULT 0,
                line INTEGER NOT NULL DEFAULT 1,
                column_number INTEGER NOT NULL DEFAULT 1,
                context_preview TEXT NOT NULL DEFAULT '',
                resolved_document_id TEXT,
                resolution_status TEXT NOT NULL DEFAULT 'unresolved',
                is_resolved INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(source_id) REFERENCES knowledge_sources(id) ON DELETE CASCADE,
                FOREIGN KEY(source_document_id) REFERENCES knowledge_documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS knowledge_scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                added_count INTEGER NOT NULL,
                updated_count INTEGER NOT NULL,
                deleted_count INTEGER NOT NULL,
                unchanged_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                FOREIGN KEY(source_id) REFERENCES knowledge_sources(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_documents_source
                ON knowledge_documents(source_id);
            CREATE INDEX IF NOT EXISTS idx_tags_source_tag
                ON knowledge_tags(source_id, tag);
            CREATE INDEX IF NOT EXISTS idx_links_source_target
                ON knowledge_links(source_id, target);
            """
        )
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(knowledge_links)")
        }
        source_columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(knowledge_sources)")
        }
        if "allow_as_shared_link_target" not in source_columns:
            connection.execute(
                "ALTER TABLE knowledge_sources ADD COLUMN "
                "allow_as_shared_link_target INTEGER NOT NULL DEFAULT 0"
            )
        if "resolution_status" not in columns:
            connection.execute(
                "ALTER TABLE knowledge_links ADD COLUMN "
                "resolution_status TEXT NOT NULL DEFAULT 'unresolved'"
            )
        if "display_text" not in columns:
            connection.execute(
                "ALTER TABLE knowledge_links ADD COLUMN display_text TEXT"
            )
        migrations = {
            "raw_target": "TEXT NOT NULL DEFAULT ''",
            "normalized_target": "TEXT NOT NULL DEFAULT ''",
            "heading": "TEXT",
            "is_resolved": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "occurrence_id": "TEXT NOT NULL DEFAULT ''",
            "raw_text": "TEXT NOT NULL DEFAULT ''",
            "start_offset": "INTEGER NOT NULL DEFAULT 0",
            "end_offset": "INTEGER NOT NULL DEFAULT 0",
            "line": "INTEGER NOT NULL DEFAULT 1",
            "column_number": "INTEGER NOT NULL DEFAULT 1",
            "context_preview": "TEXT NOT NULL DEFAULT ''",
        }
        for column, declaration in migrations.items():
            if column not in columns:
                connection.execute(
                    f"ALTER TABLE knowledge_links ADD COLUMN {column} {declaration}"
                )
        connection.execute(
            "UPDATE knowledge_links SET raw_target = target WHERE raw_target = ''"
        )
        connection.execute(
            "UPDATE knowledge_links SET normalized_target = target "
            "WHERE normalized_target = ''"
        )
        if force_like_search:
            self.fts_enabled = False
            return
        try:
            connection.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    document_id UNINDEXED,
                    title,
                    relative_path,
                    content
                )
                """
            )
            self.fts_enabled = True
        except sqlite3.OperationalError:
            self.fts_enabled = False

    def upsert_source(self, source: KnowledgeSource) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_sources (
                    id, name, path, category, source_type, enabled, sensitive,
                    allow_agent_access, created_at, last_scanned_at
                    , allow_as_shared_link_target
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    path = excluded.path,
                    category = excluded.category,
                    source_type = excluded.source_type,
                    enabled = excluded.enabled,
                    sensitive = excluded.sensitive,
                    allow_agent_access = excluded.allow_agent_access,
                    allow_as_shared_link_target = excluded.allow_as_shared_link_target,
                    last_scanned_at = excluded.last_scanned_at
                """,
                (
                    source.id,
                    source.name,
                    str(source.path),
                    source.category,
                    source.source_type,
                    source.enabled,
                    source.sensitive,
                    source.allow_agent_access,
                    source.created_at.isoformat(),
                    source.last_scanned_at.isoformat()
                    if source.last_scanned_at
                    else None,
                    source.allow_as_shared_link_target,
                ),
            )

    def document_state(self, source_id: str) -> dict[str, tuple[str, int, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT relative_path, content_hash, file_size, modified_at
                FROM knowledge_documents WHERE source_id = ?
                """,
                (source_id,),
            ).fetchall()
        return {
            str(row["relative_path"]): (
                str(row["content_hash"]),
                int(row["file_size"]),
                str(row["modified_at"]),
            )
            for row in rows
        }

    def save_document(self, document: KnowledgeDocument) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_documents (
                    id, source_id, relative_path, absolute_path, title, content,
                    aliases, modified_at, indexed_at, content_hash, file_size
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    relative_path = excluded.relative_path,
                    absolute_path = excluded.absolute_path,
                    title = excluded.title,
                    content = excluded.content,
                    aliases = excluded.aliases,
                    modified_at = excluded.modified_at,
                    indexed_at = excluded.indexed_at,
                    content_hash = excluded.content_hash,
                    file_size = excluded.file_size
                """,
                (
                    document.id,
                    document.source_id,
                    document.relative_path,
                    str(document.absolute_path),
                    document.title,
                    document.content,
                    json.dumps(document.aliases, ensure_ascii=False),
                    document.modified_at.isoformat(),
                    document.indexed_at.isoformat(),
                    document.content_hash,
                    document.file_size,
                ),
            )
            connection.execute(
                "DELETE FROM knowledge_tags WHERE source_id = ? AND document_id = ?",
                (document.source_id, document.id),
            )
            connection.executemany(
                """
                INSERT INTO knowledge_tags (source_id, document_id, tag)
                VALUES (?, ?, ?)
                """,
                ((document.source_id, document.id, tag) for tag in document.tags),
            )
            connection.execute(
                """
                DELETE FROM knowledge_links
                WHERE source_id = ? AND source_document_id = ?
                """,
                (document.source_id, document.id),
            )
            connection.executemany(
                """
                INSERT INTO knowledge_links (
                    source_id, source_document_id, target, raw_target,
                    normalized_target, link_type, heading, display_text,
                    occurrence_id, raw_text, start_offset, end_offset, line,
                    column_number, context_preview, resolved_document_id,
                    is_resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, ?)
                """,
                (
                    (
                        document.source_id,
                        document.id,
                        link.target,
                        link.raw_target or link.target,
                        link.target,
                        link.link_type,
                        link.heading,
                        link.display_text,
                        link.occurrence_id,
                        link.raw_text,
                        link.start_offset,
                        link.end_offset,
                        link.line,
                        link.column,
                        link.context_preview,
                        document.indexed_at.isoformat(),
                    )
                    for link in document.outgoing_links
                ),
            )
            if self.fts_enabled:
                connection.execute(
                    "DELETE FROM knowledge_fts WHERE document_id = ?", (document.id,)
                )
                connection.execute(
                    """
                    INSERT INTO knowledge_fts (document_id, title, relative_path, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        document.id,
                        document.title,
                        document.relative_path,
                        document.content,
                    ),
                )

    def delete_documents(self, source_id: str, relative_paths: Iterable[str]) -> int:
        paths = tuple(relative_paths)
        if not paths:
            return 0
        placeholders = ",".join("?" for _ in paths)
        with self._connect() as connection:
            ids = [
                str(row["id"])
                for row in connection.execute(
                    f"""
                    SELECT id FROM knowledge_documents
                    WHERE source_id = ? AND relative_path IN ({placeholders})
                    """,
                    (source_id, *paths),
                ).fetchall()
            ]
            if self.fts_enabled and ids:
                id_placeholders = ",".join("?" for _ in ids)
                connection.execute(
                    f"DELETE FROM knowledge_fts WHERE document_id IN ({id_placeholders})",
                    ids,
                )
            cursor = connection.execute(
                f"""
                DELETE FROM knowledge_documents
                WHERE source_id = ? AND relative_path IN ({placeholders})
                """,
                (source_id, *paths),
            )
            return cursor.rowcount

    def remove_source(self, source_id: str) -> None:
        with self._connect() as connection:
            if self.fts_enabled:
                connection.execute(
                    """
                    DELETE FROM knowledge_fts WHERE document_id IN (
                        SELECT id FROM knowledge_documents WHERE source_id = ?
                    )
                    """,
                    (source_id,),
                )
            connection.execute(
                "DELETE FROM knowledge_sources WHERE id = ?", (source_id,)
            )

    def document_count(self, source_id: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM knowledge_documents WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def record_scan(
        self, result: ScanResult, started_at: datetime, finished_at: datetime
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO knowledge_scan_history (
                    source_id, started_at, finished_at, added_count, updated_count,
                    deleted_count, unchanged_count, error_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.source.id,
                    started_at.isoformat(),
                    finished_at.isoformat(),
                    result.added_count,
                    result.updated_count,
                    result.deleted_count,
                    result.unchanged_count,
                    result.error_count,
                ),
            )

    def resolve_links(self, source_id: str) -> None:
        """Resolve local links and explicit links to approved shared sources."""

        with self._connect() as connection:
            source_rows = connection.execute(
                """
                SELECT id, name, enabled, allow_as_shared_link_target
                FROM knowledge_sources
                """
            ).fetchall()
            documents = connection.execute(
                """
                SELECT id, source_id, relative_path, title, aliases
                FROM knowledge_documents
                """
            ).fetchall()
            links = connection.execute(
                """
                SELECT l.id, l.source_document_id,
                       l.normalized_target AS target, l.link_type,
                       d.relative_path AS source_path
                FROM knowledge_links l
                JOIN knowledge_documents d ON d.id = l.source_document_id
                WHERE l.source_id = ?
                """,
                (source_id,),
            ).fetchall()

            source_by_reference: dict[str, tuple[str, bool]] = {}
            for row in source_rows:
                if not bool(row["enabled"]):
                    continue
                value = (str(row["id"]), bool(row["allow_as_shared_link_target"]))
                source_by_reference[str(row["id"]).casefold()] = value
                source_by_reference[str(row["name"]).casefold()] = value

            maps: dict[str, tuple[dict[str, set[str]], dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]]] = {}
            for document in documents:
                document_id = str(document["id"])
                document_source_id = str(document["source_id"])
                paths, stems, titles, aliases = maps.setdefault(
                    document_source_id, ({}, {}, {}, {})
                )
                relative_path = str(document["relative_path"])
                self._add_candidate(paths, self._path_key(relative_path), document_id)
                self._add_candidate(
                    stems, self._text_key(Path(relative_path).stem), document_id
                )
                self._add_candidate(
                    titles, self._text_key(str(document["title"])), document_id
                )
                for alias in json.loads(str(document["aliases"])):
                    self._add_candidate(
                        aliases, self._text_key(str(alias)), document_id
                    )

            updates: list[tuple[str | None, str, int]] = []
            for link in links:
                link_type = str(link["link_type"])
                if link_type == "external_url":
                    updates.append((None, "external", int(link["id"])))
                    continue
                if link_type == "attachment":
                    updates.append((None, "attachment", int(link["id"])))
                    continue
                if link_type not in {"wiki_link", "internal_markdown"}:
                    updates.append((None, "unresolved", int(link["id"])))
                    continue
                raw_target = str(link["target"]).split("#", 1)[0].strip()
                target_source_id = source_id
                explicit_source = False
                if "::" in raw_target:
                    source_reference, raw_target = raw_target.split("::", 1)
                    target_source = source_by_reference.get(
                        source_reference.strip().casefold()
                    )
                    if not target_source or not target_source[1]:
                        updates.append((None, "unresolved", int(link["id"])))
                        continue
                    target_source_id = target_source[0]
                    explicit_source = True
                paths, stems, titles, aliases = maps.get(
                    target_source_id, ({}, {}, {}, {})
                )
                source_directory = posixpath.dirname(str(link["source_path"]))
                path_candidates = [self._path_key(raw_target)]
                if not explicit_source and (link_type == "internal_markdown" or raw_target.startswith(
                    (".", "..")
                )):
                    path_candidates.insert(
                        0,
                        self._path_key(posixpath.join(source_directory, raw_target)),
                    )
                resolved, status = self._resolve_candidates(paths, path_candidates)
                if status == "unresolved":
                    target_stem = Path(raw_target).stem
                    resolved, status = self._resolve_candidates(
                        stems, [self._text_key(target_stem)]
                    )
                if status == "unresolved":
                    resolved, status = self._resolve_candidates(
                        titles, [self._text_key(raw_target)]
                    )
                if status == "unresolved":
                    resolved, status = self._resolve_candidates(
                        aliases, [self._text_key(raw_target)]
                    )
                updates.append((resolved, status, int(link["id"])))

            connection.executemany(
                """
                UPDATE knowledge_links
                SET resolved_document_id = ?, resolution_status = ?,
                    is_resolved = CASE WHEN ? = 'resolved' THEN 1 ELSE 0 END
                WHERE id = ?
                """,
                (
                    (resolved, status, status, link_id)
                    for resolved, status, link_id in updates
                ),
            )

    def resolve_all_links(self) -> None:
        """Re-resolve every source so shared-target changes update backlinks."""

        with self._connect() as connection:
            source_ids = tuple(
                str(row["id"])
                for row in connection.execute(
                    "SELECT id FROM knowledge_sources WHERE enabled = 1 ORDER BY id"
                )
            )
        for source_id in source_ids:
            self.resolve_links(source_id)

    def graph_records(
        self, source_id: str
    ) -> tuple[tuple[GraphDocumentRecord, ...], tuple[GraphLinkRecord, ...]]:
        """Return source-scoped records consumed by the graph query service."""

        with self._connect() as connection:
            link_rows = connection.execute(
                """
                SELECT l.id, l.source_document_id, l.resolved_document_id,
                       l.normalized_target AS target,
                       l.link_type, l.resolution_status, l.display_text, l.raw_target,
                       l.occurrence_id, l.raw_text, l.start_offset, l.end_offset, l.line,
                       l.column_number, l.context_preview
                FROM knowledge_links l
                WHERE (l.source_id = ? OR l.resolved_document_id IN (
                    SELECT id FROM knowledge_documents WHERE source_id = ?
                ))
                  AND l.link_type IN ('wiki_link', 'internal_markdown')
                ORDER BY l.id
                """,
                (source_id, source_id),
            ).fetchall()
            related_ids = {
                str(value)
                for row in link_rows
                for value in (row["source_document_id"], row["resolved_document_id"])
                if value is not None
            }
            placeholders = ",".join("?" for _ in related_ids)
            condition = "d.source_id = ?"
            parameters: list[object] = [source_id]
            if related_ids:
                condition += f" OR d.id IN ({placeholders})"
                parameters.extend(sorted(related_ids))
            document_rows = connection.execute(
                """
                SELECT d.id, d.source_id, d.title, d.relative_path, d.aliases,
                       d.modified_at, d.indexed_at, d.content, d.content_hash,
                       s.category
                FROM knowledge_documents d
                JOIN knowledge_sources s ON s.id = d.source_id
                WHERE """ + condition + """
                ORDER BY d.title COLLATE NOCASE, d.relative_path COLLATE NOCASE
                """,
                parameters,
            ).fetchall()
            document_ids = tuple(str(row["id"]) for row in document_rows)
            tag_placeholders = ",".join("?" for _ in document_ids)
            tag_rows = connection.execute(
                """
                SELECT document_id, tag FROM knowledge_tags
                WHERE document_id IN (""" + tag_placeholders + ") ORDER BY tag COLLATE NOCASE",
                document_ids,
            ).fetchall() if document_ids else []
        tags: dict[str, list[str]] = {}
        for row in tag_rows:
            tags.setdefault(str(row["document_id"]), []).append(str(row["tag"]))
        documents = tuple(
            GraphDocumentRecord(
                id=str(row["id"]),
                source_id=str(row["source_id"]),
                title=str(row["title"]),
                relative_path=str(row["relative_path"]),
                category=str(row["category"]),
                tags=tuple(tags.get(str(row["id"]), ())),
                aliases=tuple(json.loads(str(row["aliases"]))),
                modified_at=datetime.fromisoformat(str(row["modified_at"])),
                indexed_at=datetime.fromisoformat(str(row["indexed_at"])),
                content=str(row["content"]),
                content_hash=str(row["content_hash"]),
            )
            for row in document_rows
        )
        links = tuple(
            GraphLinkRecord(
                id=int(row["id"]),
                source_document_id=str(row["source_document_id"]),
                target_document_id=(
                    str(row["resolved_document_id"])
                    if row["resolved_document_id"] is not None
                    else None
                ),
                target=str(row["target"]),
                link_type=str(row["link_type"]),
                resolution_status=str(row["resolution_status"]),
                display_text=(
                    str(row["display_text"])
                    if row["display_text"] is not None
                    else None
                ),
                raw_target=str(row["raw_target"]),
                occurrence_id=str(row["occurrence_id"]),
                raw_text=str(row["raw_text"]),
                start_offset=int(row["start_offset"]),
                end_offset=int(row["end_offset"]),
                line=int(row["line"]),
                column=int(row["column_number"]),
                context_preview=str(row["context_preview"]),
            )
            for row in link_rows
        )
        return documents, links

    @staticmethod
    def _add_candidate(
        mapping: dict[str, set[str]], key: str, document_id: str
    ) -> None:
        if key:
            mapping.setdefault(key, set()).add(document_id)

    @staticmethod
    def _resolve_candidates(
        mapping: dict[str, set[str]], keys: list[str]
    ) -> tuple[str | None, str]:
        matches: set[str] = set()
        for key in keys:
            matches.update(mapping.get(key, ()))
        if len(matches) == 1:
            return next(iter(matches)), "resolved"
        if len(matches) > 1:
            return None, "ambiguous"
        return None, "unresolved"

    @staticmethod
    def _path_key(value: str) -> str:
        normalized = posixpath.normpath(value.strip().replace("\\", "/"))
        if not normalized.casefold().endswith(".md"):
            normalized = f"{normalized}.md"
        return normalized.lstrip("./").casefold()

    @staticmethod
    def _text_key(value: str) -> str:
        return " ".join(value.casefold().split())

    def search(
        self,
        *,
        source_ids: tuple[str, ...],
        query: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> tuple[SearchResult, ...]:
        if not source_ids:
            return ()
        placeholders = ",".join("?" for _ in source_ids)
        joins = ["JOIN knowledge_sources s ON s.id = d.source_id"]
        conditions = [f"d.source_id IN ({placeholders})"]
        parameters: list[Any] = list(source_ids)
        if tag:
            conditions.append(
                "EXISTS (SELECT 1 FROM knowledge_tags t "
                "WHERE t.document_id = d.id AND t.source_id = d.source_id AND t.tag = ?)"
            )
            parameters.append(tag.lstrip("#"))
        if query:
            if self.fts_enabled:
                joins.append("JOIN knowledge_fts ON knowledge_fts.document_id = d.id")
                conditions.append("knowledge_fts MATCH ?")
                parameters.append(f'"{query.replace(chr(34), chr(34) * 2)}"')
            else:
                conditions.append(
                    "(d.title LIKE ? OR d.relative_path LIKE ? OR d.content LIKE ?)"
                )
                pattern = f"%{query}%"
                parameters.extend((pattern, pattern, pattern))
        parameters.append(max(1, limit))
        sql = f"""
            SELECT d.id, d.source_id, d.title, d.relative_path, d.content,
                   s.name AS source_name, s.category, s.sensitive
            FROM knowledge_documents d
            {" ".join(joins)}
            WHERE {" AND ".join(conditions)}
            ORDER BY d.title COLLATE NOCASE, d.relative_path COLLATE NOCASE
            LIMIT ?
        """
        try:
            with self._connect() as connection:
                rows = connection.execute(sql, parameters).fetchall()
        except sqlite3.OperationalError as error:
            raise KnowledgeDatabaseError("Knowledge search failed.") from error
        return tuple(self._search_result(row, query) for row in rows)

    def backlinks(
        self, *, source_id: str, document: str, limit: int = 100
    ) -> tuple[SearchResult, ...]:
        target = document.strip()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, relative_path, title, aliases FROM knowledge_documents
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchall()
            target_key = self._text_key(target)
            target_ids = [
                str(row["id"])
                for row in rows
                if target_key
                in {
                    self._text_key(str(row["id"])),
                    self._text_key(str(row["title"])),
                    self._text_key(str(row["relative_path"])),
                    self._text_key(Path(str(row["relative_path"])).stem),
                    *(
                        self._text_key(str(alias))
                        for alias in json.loads(str(row["aliases"]))
                    ),
                }
            ]
            if not target_ids:
                return ()
            placeholders = ",".join("?" for _ in target_ids)
            results = connection.execute(
                f"""
                SELECT DISTINCT d.id, d.source_id, d.title, d.relative_path, d.content,
                       s.name AS source_name, s.category, s.sensitive
                FROM knowledge_links l
                JOIN knowledge_documents d ON d.id = l.source_document_id
                JOIN knowledge_sources s ON s.id = d.source_id
                WHERE l.source_id = ?
                  AND l.resolution_status = 'resolved'
                  AND l.resolved_document_id IN ({placeholders})
                ORDER BY d.relative_path COLLATE NOCASE
                LIMIT ?
                """,
                (source_id, *target_ids, max(1, limit)),
            ).fetchall()
        return tuple(self._search_result(row, None) for row in results)

    @staticmethod
    def _search_result(row: sqlite3.Row, query: str | None) -> SearchResult:
        content = " ".join(str(row["content"]).split())
        if query:
            index = content.casefold().find(query.casefold())
            start = max(0, index - 60) if index >= 0 else 0
        else:
            start = 0
        snippet = content[start : start + 180]
        if start:
            snippet = f"...{snippet}"
        if start + 180 < len(content):
            snippet = f"{snippet}..."
        return SearchResult(
            source_id=str(row["source_id"]),
            source_name=str(row["source_name"]),
            category=str(row["category"]),
            sensitive=bool(row["sensitive"]),
            document_id=str(row["id"]),
            title=str(row["title"]),
            relative_path=str(row["relative_path"]),
            snippet=snippet,
        )
