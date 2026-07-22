"""Source-scoped SQLite repository for the local knowledge index."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from mde.knowledge.errors import KnowledgeDatabaseError
from mde.knowledge.models import (
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
                link_type TEXT NOT NULL,
                resolved_document_id TEXT,
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
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    path = excluded.path,
                    category = excluded.category,
                    source_type = excluded.source_type,
                    enabled = excluded.enabled,
                    sensitive = excluded.sensitive,
                    allow_agent_access = excluded.allow_agent_access,
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
                    source_id, source_document_id, target, link_type, resolved_document_id
                ) VALUES (?, ?, ?, ?, NULL)
                """,
                (
                    (document.source_id, document.id, link.target, link.link_type)
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
        candidates = {target, Path(target).stem}
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT relative_path, title, aliases FROM knowledge_documents
                WHERE source_id = ? AND (
                    id = ? OR relative_path = ? OR title = ? OR
                    relative_path LIKE ?
                )
                """,
                (source_id, target, target, target, f"%/{target}.md"),
            ).fetchall()
            for row in rows:
                candidates.add(str(row["title"]))
                candidates.add(Path(str(row["relative_path"])).stem)
                candidates.add(str(row["relative_path"]))
                candidates.update(json.loads(str(row["aliases"])))
            placeholders = ",".join("?" for _ in candidates)
            results = connection.execute(
                f"""
                SELECT DISTINCT d.id, d.source_id, d.title, d.relative_path, d.content,
                       s.name AS source_name, s.category, s.sensitive
                FROM knowledge_links l
                JOIN knowledge_documents d ON d.id = l.source_document_id
                JOIN knowledge_sources s ON s.id = d.source_id
                WHERE l.source_id = ? AND l.target IN ({placeholders})
                ORDER BY d.relative_path COLLATE NOCASE
                LIMIT ?
                """,
                (source_id, *sorted(candidates), max(1, limit)),
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
