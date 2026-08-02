"""Source-scoped graph queries over the Knowledge Plugin index."""

from __future__ import annotations

from collections import deque
import os
import re

from mde.knowledge.errors import KnowledgeContractError
from mde.knowledge.models import (
    GraphDocumentRecord,
    GraphLinkRecord,
    ExtractedLink,
    KnowledgeGraph,
    KnowledgeGraphBrokenLink,
    KnowledgeDocumentDetail,
    KnowledgeDocumentReference,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeSource,
    KnowledgeTagCount,
)
from mde.knowledge.registry import SourceRegistry
from mde.knowledge.repository import KnowledgeRepository
from mde.knowledge.parser import split_frontmatter

_FRONTMATTER = re.compile(r"\A---\s*\n.*?\n---\s*(?:\n|\Z)", re.DOTALL)
_UNSAFE_HTML = re.compile(
    r"<(script|iframe)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)


class KnowledgeGraphService:
    """Build bounded source and document graphs without reading Markdown directly."""

    def __init__(
        self, registry: SourceRegistry, repository: KnowledgeRepository
    ) -> None:
        self.registry = registry
        self.repository = repository

    def get_source_graph(
        self,
        source_id: str,
        *,
        tag: str | None = None,
        query: str | None = None,
        include_orphans: bool = True,
        include_broken: bool = False,
        limit: int = 1000,
        confirm_sensitive: bool = False,
    ) -> KnowledgeGraph:
        source = self._source(source_id, confirm_sensitive=confirm_sensitive)
        self._validate_limit(limit, maximum=1000)
        documents, links = self.repository.graph_records(source.id)
        documents, links = self._visible_records(
            source, documents, links, confirm_sensitive=confirm_sensitive
        )
        selected = tuple(
            document
            for document in documents
            if self._matches(document, tag=tag, query=query)
        )
        if not include_orphans:
            connected = self._connected_ids(links)
            selected = tuple(
                document for document in selected if document.id in connected
            )
        degrees = self._degree_counts(links)
        ranked = sorted(
            selected,
            key=lambda item: (degrees.get(item.id, 0), item.modified_at, item.id),
            reverse=True,
        )
        returned = tuple(document.id for document in ranked[:limit])
        return self._build_graph(
            source,
            documents,
            links,
            returned,
            include_broken=include_broken,
            total_document_count=sum(
                document.source_id == source.id for document in documents
            ),
            truncated=len(selected) > len(returned),
        )

    def get_document_graph(
        self,
        source_id: str,
        document_id: str,
        *,
        depth: int = 1,
        direction: str = "both",
        include_broken: bool = False,
        limit: int = 300,
        confirm_sensitive: bool = False,
    ) -> KnowledgeGraph:
        source = self._source(source_id, confirm_sensitive=confirm_sensitive)
        if depth not in {1, 2, 3}:
            raise KnowledgeContractError(
                "INVALID_DEPTH", "Graph depth must be between 1 and 3."
            )
        if direction not in {"incoming", "outgoing", "both"}:
            raise KnowledgeContractError(
                "INVALID_DIRECTION",
                "Graph direction must be incoming, outgoing, or both.",
            )
        self._validate_limit(limit, maximum=300)
        documents, links = self.repository.graph_records(source.id)
        documents, links = self._visible_records(
            source, documents, links, confirm_sensitive=confirm_sensitive
        )
        document_ids = {document.id for document in documents}
        if document_id not in document_ids:
            raise KnowledgeContractError(
                "DOCUMENT_NOT_FOUND", "Knowledge document was not found."
            )

        outgoing: dict[str, set[str]] = {}
        incoming: dict[str, set[str]] = {}
        for link in links:
            if link.resolution_status != "resolved" or not link.target_document_id:
                continue
            outgoing.setdefault(link.source_document_id, set()).add(
                link.target_document_id
            )
            incoming.setdefault(link.target_document_id, set()).add(
                link.source_document_id
            )

        selected = {document_id}
        queue: deque[tuple[str, int]] = deque([(document_id, 0)])
        visit_order = [document_id]
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            neighbors: set[str] = set()
            if direction in {"outgoing", "both"}:
                neighbors.update(outgoing.get(current, ()))
            if direction in {"incoming", "both"}:
                neighbors.update(incoming.get(current, ()))
            for neighbor in sorted(neighbors):
                if neighbor in selected:
                    continue
                selected.add(neighbor)
                visit_order.append(neighbor)
                queue.append((neighbor, current_depth + 1))
        ordered_ids = tuple(visit_order[:limit])
        return self._build_graph(
            source,
            documents,
            links,
            ordered_ids,
            include_broken=include_broken,
            total_document_count=len(selected),
            truncated=len(selected) > len(ordered_ids),
        )

    def get_document_detail(
        self,
        source_id: str,
        document_id: str,
        *,
        confirm_sensitive: bool = False,
    ) -> KnowledgeDocumentDetail:
        source = self._source(source_id, confirm_sensitive=confirm_sensitive)
        documents, links = self.repository.graph_records(source.id)
        documents, links = self._visible_records(
            source, documents, links, confirm_sensitive=confirm_sensitive
        )
        document = next((item for item in documents if item.id == document_id), None)
        if document is None:
            raise KnowledgeContractError(
                "DOCUMENT_NOT_FOUND", "Knowledge document was not found."
            )
        by_id = {item.id: item for item in documents}
        outgoing_ids = tuple(
            link.target_document_id
            for link in links
            if link.source_document_id == document.id
            and link.resolution_status == "resolved"
            and link.target_document_id
        )
        incoming_ids = tuple(
            link.source_document_id
            for link in links
            if link.target_document_id == document.id
            and link.resolution_status == "resolved"
        )
        unresolved = tuple(
            link.target
            for link in links
            if link.source_document_id == document.id
            and link.resolution_status == "unresolved"
        )
        ambiguous = tuple(
            link.target
            for link in links
            if link.source_document_id == document.id
            and link.resolution_status == "ambiguous"
        )
        frontmatter, body, _, _ = split_frontmatter(document.content.lstrip("\ufeff"))
        unresolved_occurrences = tuple(
            ExtractedLink(
                target=link.target,
                link_type=link.link_type,
                display_text=link.display_text,
                raw_target=link.raw_target,
                occurrence_id=link.occurrence_id,
                raw_text=link.raw_text,
                start_offset=link.start_offset,
                end_offset=link.end_offset,
                line=link.line,
                column=link.column,
                context_preview=link.context_preview,
                resolution_status=link.resolution_status,
            )
            for link in links
            if link.source_document_id == document.id
            and link.resolution_status in {"unresolved", "ambiguous"}
        )
        return KnowledgeDocumentDetail(
            id=document.id,
            source_id=document.source_id,
            title=document.title,
            relative_path=document.relative_path,
            category=document.category,
            tags=document.tags,
            aliases=document.aliases,
            modified_at=document.modified_at,
            indexed_at=document.indexed_at,
            preview=self._preview(document.content),
            outgoing_documents=self._references(outgoing_ids, by_id),
            incoming_documents=self._references(incoming_ids, by_id),
            unresolved_links=tuple(dict.fromkeys(unresolved)),
            ambiguous_links=tuple(dict.fromkeys(ambiguous)),
            body=body,
            raw_content=document.content,
            frontmatter=frontmatter,
            content_hash=document.content_hash,
            editable=(
                not source.read_only
                and source.editable_in_viewer
                and os.access(source.path, os.W_OK)
            ),
            unresolved_occurrences=unresolved_occurrences,
        )

    def get_tags(
        self, source_id: str, *, confirm_sensitive: bool = False
    ) -> tuple[KnowledgeTagCount, ...]:
        source = self._source(source_id, confirm_sensitive=confirm_sensitive)
        documents, _ = self.repository.graph_records(source.id)
        counts: dict[str, int] = {}
        for document in documents:
            if document.source_id != source.id:
                continue
            for tag in set(document.tags):
                counts[tag] = counts.get(tag, 0) + 1
        return tuple(
            KnowledgeTagCount(name=name, document_count=count)
            for name, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0].casefold())
            )
        )

    def search_documents(
        self,
        query: str,
        *,
        source_id: str | None = None,
        confirm_sensitive: bool = False,
        tag: str | None = None,
        limit: int = 20,
    ) -> tuple[GraphDocumentRecord, ...]:
        needle = query.strip().casefold()
        if not needle:
            raise KnowledgeContractError("INVALID_QUERY", "Search query is required.")
        self._validate_limit(limit, maximum=100)
        if source_id:
            sources = (self._source(source_id, confirm_sensitive=confirm_sensitive),)
        else:
            sources = tuple(
                source
                for source in self.registry.list()
                if source.enabled
                and not source.sensitive
                and source.category in {"development", "project", "shared"}
            )
        results: list[GraphDocumentRecord] = []
        for source in sources:
            documents, _ = self.repository.graph_records(source.id)
            results.extend(
                document
                for document in documents
                if document.source_id == source.id
                if not tag
                or tag.lstrip("#").casefold()
                in {item.casefold() for item in document.tags}
                if needle
                in " ".join(
                    (
                        document.title,
                        document.relative_path,
                        *document.aliases,
                        document.content,
                    )
                ).casefold()
            )
        def rank(document: GraphDocumentRecord) -> tuple[int, str, str]:
            title = document.title.casefold()
            aliases = {item.casefold() for item in document.aliases}
            stem = document.relative_path.rsplit("/", 1)[-1].removesuffix(".md").casefold()
            path = document.relative_path.casefold()
            if title == needle:
                priority = 0
            elif needle in aliases:
                priority = 1
            elif stem == needle:
                priority = 2
            elif needle in title:
                priority = 3
            elif needle in path:
                priority = 4
            else:
                priority = 5
            return priority, title, path

        return tuple(sorted(results, key=rank)[:limit])

    def _source(self, source_id: str, *, confirm_sensitive: bool) -> KnowledgeSource:
        source = self.registry.get(source_id)
        if not source.enabled:
            raise KnowledgeContractError(
                "SOURCE_DISABLED", "Knowledge source is disabled."
            )
        if source.sensitive and not confirm_sensitive:
            raise KnowledgeContractError(
                "SENSITIVE_SOURCE_NOT_ALLOWED",
                "Sensitive source access requires explicit confirmation.",
            )
        return source

    def _visible_records(
        self,
        source: KnowledgeSource,
        documents: tuple[GraphDocumentRecord, ...],
        links: tuple[GraphLinkRecord, ...],
        *,
        confirm_sensitive: bool,
    ) -> tuple[tuple[GraphDocumentRecord, ...], tuple[GraphLinkRecord, ...]]:
        """Hide cross-source sensitive records unless access was confirmed."""

        sources = {item.id: item for item in self.registry.list()}
        visible_documents = tuple(
            document
            for document in documents
            if document.source_id == source.id
            or (
                document.source_id in sources
                and sources[document.source_id].enabled
                and (
                    not sources[document.source_id].sensitive
                    or confirm_sensitive
                )
            )
        )
        visible_ids = {document.id for document in visible_documents}
        visible_links = tuple(
            link
            for link in links
            if link.source_document_id in visible_ids
            and (
                link.target_document_id is None
                or link.target_document_id in visible_ids
            )
        )
        return visible_documents, visible_links

    @staticmethod
    def _validate_limit(limit: int, *, maximum: int) -> None:
        if limit < 1 or limit > maximum:
            raise KnowledgeContractError(
                "INVALID_LIMIT", f"Graph limit must be between 1 and {maximum}."
            )

    @staticmethod
    def _matches(
        document: GraphDocumentRecord, *, tag: str | None, query: str | None
    ) -> bool:
        if tag and tag.lstrip("#").casefold() not in {
            item.casefold() for item in document.tags
        }:
            return False
        if query:
            needle = query.casefold().strip()
            if not needle:
                raise KnowledgeContractError(
                    "INVALID_QUERY", "Search query must not be blank."
                )
            haystack = " ".join(
                (document.title, document.relative_path, document.content)
            ).casefold()
            if needle not in haystack:
                return False
        return True

    @staticmethod
    def _connected_ids(links: tuple[GraphLinkRecord, ...]) -> set[str]:
        connected: set[str] = set()
        for link in links:
            if link.resolution_status == "resolved" and link.target_document_id:
                connected.add(link.source_document_id)
                connected.add(link.target_document_id)
        return connected

    @staticmethod
    def _build_graph(
        source: KnowledgeSource,
        documents: tuple[GraphDocumentRecord, ...],
        links: tuple[GraphLinkRecord, ...],
        selected_ids: tuple[str, ...],
        *,
        include_broken: bool,
        total_document_count: int,
        truncated: bool,
    ) -> KnowledgeGraph:
        selected = set(selected_ids)
        incoming: dict[str, int] = {document.id: 0 for document in documents}
        outgoing: dict[str, int] = {document.id: 0 for document in documents}
        broken: dict[str, int] = {document.id: 0 for document in documents}
        edges: list[KnowledgeGraphEdge] = []
        broken_links: list[KnowledgeGraphBrokenLink] = []
        for link in links:
            if link.resolution_status == "resolved" and link.target_document_id:
                outgoing[link.source_document_id] += 1
                incoming[link.target_document_id] += 1
                if (
                    link.source_document_id in selected
                    and link.target_document_id in selected
                ):
                    edges.append(
                        KnowledgeGraphEdge(
                            id=f"link-{link.id}",
                            source=link.source_document_id,
                            target=link.target_document_id,
                            link_type=link.link_type,
                            display_text=link.display_text,
                        )
                    )
            else:
                broken[link.source_document_id] += 1
                if include_broken and link.source_document_id in selected:
                    broken_links.append(
                        KnowledgeGraphBrokenLink(
                            id=f"link-{link.id}",
                            source_document_id=link.source_document_id,
                            target=link.target,
                            link_type=link.link_type,
                            resolution_status=link.resolution_status,
                        )
                    )
        nodes = tuple(
            KnowledgeGraphNode(
                id=document.id,
                source_id=document.source_id,
                title=document.title,
                relative_path=document.relative_path,
                category=document.category,
                tags=document.tags,
                incoming_count=incoming[document.id],
                outgoing_count=outgoing[document.id],
                broken_outgoing_count=broken[document.id],
                is_orphan=(incoming[document.id] == 0 and outgoing[document.id] == 0),
                modified_at=document.modified_at,
            )
            for document in documents
            if document.id in selected
        )
        return KnowledgeGraph(
            source=source,
            nodes=nodes,
            edges=tuple(edges),
            broken_links=tuple(broken_links),
            total_document_count=total_document_count,
            returned_document_count=len(nodes),
            truncated=truncated,
        )

    @staticmethod
    def _references(
        document_ids: tuple[str, ...],
        documents: dict[str, GraphDocumentRecord],
    ) -> tuple[KnowledgeDocumentReference, ...]:
        unique_ids = tuple(dict.fromkeys(document_ids))
        return tuple(
            KnowledgeDocumentReference(
                document_id=document_id,
                source_id=documents[document_id].source_id,
                title=documents[document_id].title,
            )
            for document_id in unique_ids
            if document_id in documents
        )

    @staticmethod
    def _degree_counts(links: tuple[GraphLinkRecord, ...]) -> dict[str, int]:
        degrees: dict[str, int] = {}
        for link in links:
            if link.resolution_status != "resolved" or not link.target_document_id:
                continue
            degrees[link.source_document_id] = (
                degrees.get(link.source_document_id, 0) + 1
            )
            degrees[link.target_document_id] = (
                degrees.get(link.target_document_id, 0) + 1
            )
        return degrees

    @staticmethod
    def _preview(content: str) -> str:
        without_frontmatter = _FRONTMATTER.sub("", content)
        return _UNSAFE_HTML.sub("", without_frontmatter).strip()[:2000]
