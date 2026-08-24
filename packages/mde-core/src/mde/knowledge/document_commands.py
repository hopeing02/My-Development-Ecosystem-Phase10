"""Command orchestration for explicit Knowledge Viewer document changes."""

from __future__ import annotations

from dataclasses import dataclass
import difflib
import os
from pathlib import Path, PurePosixPath
import posixpath
import re

from mde.knowledge.document_writer import KnowledgeDocumentWriter
from mde.knowledge.errors import KnowledgeContractError
from mde.knowledge.models import GraphDocumentRecord, KnowledgeSource
from mde.knowledge.parser import parse_markdown, split_frontmatter
from mde.knowledge.service import KnowledgeService


@dataclass(frozen=True)
class DocumentUpdate:
    expected_content_hash: str
    title: str
    tags: list[str]
    aliases: list[str]
    body: str
    create_backup: bool = True


class KnowledgeDocumentCommandService:
    def __init__(self, service: KnowledgeService, writer: KnowledgeDocumentWriter | None = None) -> None:
        self.service = service
        self.writer = writer or KnowledgeDocumentWriter()
        self.graph_revision = 0

    def preview_update(self, source_id: str, document_id: str, update: DocumentUpdate, *, confirm_sensitive: bool) -> dict[str, object]:
        source, document, path, _, current, _ = self._current(source_id, document_id, update.expected_content_hash, confirm_sensitive=confirm_sensitive)
        rendered = self.writer.assemble(current, title=update.title, tags=update.tags, aliases=update.aliases, body=update.body)
        before = parse_markdown(current, path)
        after = parse_markdown(rendered, path)
        changed_lines = sum(1 for line in difflib.ndiff(current.splitlines(), rendered.splitlines()) if line.startswith(("+ ", "- ")))
        return {
            "before": {"title": before.title, "tags": list(before.tags), "aliases": list(before.aliases)},
            "after": {"title": after.title, "tags": list(after.tags), "aliases": list(after.aliases)},
            "bodyChangedLineCount": changed_lines,
            "linksAdded": self._link_delta(before.outgoing_links, after.outgoing_links),
            "linksRemoved": self._link_delta(after.outgoing_links, before.outgoing_links),
            "sourceId": source.id,
        }

    def update_document(self, source_id: str, document_id: str, update: DocumentUpdate, *, confirm_sensitive: bool) -> dict[str, object]:
        source, document, path, _, current, bom = self._current(source_id, document_id, update.expected_content_hash, confirm_sensitive=confirm_sensitive)
        rendered = self.writer.assemble(current, title=update.title, tags=update.tags, aliases=update.aliases, body=update.body)
        backup = self.writer.write(path, rendered, source_root=source.path, relative_path=document.relative_path, create_backup=update.create_backup, bom=bom)
        return self._reindex(source, document, backup)

    def preview_link_resolution(self, source_id: str, document_id: str, *, expected_content_hash: str, occurrence_id: str, target_document_id: str, link_style: str, confirm_sensitive: bool) -> dict[str, object]:
        source, document, path, _, current, _ = self._current(source_id, document_id, expected_content_hash, confirm_sensitive=confirm_sensitive, require_link_rewrite=True)
        occurrence, target, replacement = self._link_replacement(source, document, path, current, occurrence_id, target_document_id, link_style)
        return {"before": occurrence.raw_text, "after": replacement, "target": {"id": target.id, "title": target.title, "relativePath": target.relative_path}}

    def resolve_link(self, source_id: str, document_id: str, *, expected_content_hash: str, occurrence_id: str, target_document_id: str, link_style: str, create_backup: bool, confirm_sensitive: bool) -> dict[str, object]:
        source, document, path, _, current, bom = self._current(source_id, document_id, expected_content_hash, confirm_sensitive=confirm_sensitive, require_link_rewrite=True)
        occurrence, _, replacement = self._link_replacement(source, document, path, current, occurrence_id, target_document_id, link_style)
        rendered = current[: occurrence.start_offset] + replacement + current[occurrence.end_offset :]
        backup = self.writer.write(path, rendered, source_root=source.path, relative_path=document.relative_path, create_backup=create_backup, bom=bom)
        return self._reindex(source, document, backup)

    def append_child_link(
        self,
        source_id: str,
        parent_document_id: str,
        target_document_id: str,
        *,
        confirm_sensitive: bool,
    ) -> dict[str, object]:
        """Append one explicit child link to an authorized parent document."""

        source = self.service.registry.get(source_id)
        self._authorize(
            source,
            confirm_sensitive=confirm_sensitive,
            require_link_rewrite=True,
        )
        documents, links = self.service.repository.graph_records(source.id)
        parent = next(
            (
                item
                for item in documents
                if item.id == parent_document_id and item.source_id == source.id
            ),
            None,
        )
        target = next(
            (
                item
                for item in documents
                if item.id == target_document_id and item.source_id == source.id
            ),
            None,
        )
        if parent is None or target is None:
            raise KnowledgeContractError(
                "LINK_TARGET_NOT_FOUND",
                "Parent and child documents must exist in the same source.",
            )
        if parent.id == target.id:
            raise KnowledgeContractError(
                "INVALID_LINK_OCCURRENCE", "A document cannot be its own parent."
            )
        already_linked = any(
            link.source_document_id == parent.id
            and link.target_document_id == target.id
            and link.resolution_status == "resolved"
            for link in links
        )
        if already_linked:
            return {
                "fileSaved": False,
                "alreadyLinked": True,
                "parentDocumentId": parent.id,
                "targetDocumentId": target.id,
                "indexing": {"status": "completed", "documentStatus": "unchanged"},
                "graphRevision": self.graph_revision,
            }

        source, parent, path, _, current, bom = self._current(
            source.id,
            parent_document_id,
            parent.content_hash,
            confirm_sensitive=confirm_sensitive,
            require_link_rewrite=True,
        )
        _, body, _, warnings = split_frontmatter(current)
        if warnings:
            raise KnowledgeContractError(
                "INVALID_FRONTMATTER", "Existing frontmatter is invalid."
            )
        target_path = str(PurePosixPath(target.relative_path).with_suffix(""))
        link = f"[[{target_path}|{target.title}]]"
        next_body = self._append_managed_child(body, link)
        rendered = self.writer.assemble(
            current,
            title=parent.title,
            tags=list(parent.tags),
            aliases=list(parent.aliases),
            body=next_body,
        )
        backup = self.writer.write(
            path,
            rendered,
            source_root=source.path,
            relative_path=parent.relative_path,
            create_backup=True,
            bom=bom,
        )
        result = self._reindex(source, parent, backup)
        result.update(
            {
                "alreadyLinked": False,
                "parentDocumentId": parent.id,
                "targetDocumentId": target.id,
            }
        )
        return result

    def _current(self, source_id: str, document_id: str, expected_hash: str, *, confirm_sensitive: bool, require_link_rewrite: bool = False):
        source = self.service.registry.get(source_id)
        self._authorize(source, confirm_sensitive=confirm_sensitive, require_link_rewrite=require_link_rewrite)
        documents, _ = self.service.repository.graph_records(source.id)
        document = next((item for item in documents if item.id == document_id), None)
        if document is None:
            raise KnowledgeContractError("DOCUMENT_NOT_FOUND", "Knowledge document was not found.")
        path = self.writer.resolve_path(source.path, document.relative_path)
        data, current, bom = self.writer.read(path)
        current_hash = self.writer.content_hash(data)
        if expected_hash != current_hash:
            raise KnowledgeContractError("DOCUMENT_CONFLICT", "The document was modified after it was opened.", expectedContentHash=expected_hash, currentContentHash=current_hash)
        return source, document, path, data, current, bom

    @staticmethod
    def _authorize(source: KnowledgeSource, *, confirm_sensitive: bool, require_link_rewrite: bool) -> None:
        if not source.enabled:
            raise KnowledgeContractError("SOURCE_DISABLED", "Knowledge source is disabled.")
        if source.read_only:
            raise KnowledgeContractError("SOURCE_READ_ONLY", "Knowledge source is read-only.")
        if not source.editable_in_viewer:
            raise KnowledgeContractError("SOURCE_NOT_EDITABLE", "Knowledge source is not editable in Viewer.")
        if require_link_rewrite and not source.allow_link_rewrite:
            raise KnowledgeContractError("LINK_REWRITE_NOT_ALLOWED", "Link rewriting is disabled for this source.")
        if source.sensitive and not confirm_sensitive:
            raise KnowledgeContractError("SENSITIVE_SOURCE_NOT_ALLOWED", "Sensitive source editing requires explicit confirmation.")
        if not os.access(source.path, os.W_OK):
            raise KnowledgeContractError("SOURCE_NOT_EDITABLE", "Knowledge source is not writable.")

    def _link_replacement(self, source: KnowledgeSource, document: GraphDocumentRecord, path: Path, current: str, occurrence_id: str, target_document_id: str, link_style: str):
        parsed = parse_markdown(current, path)
        occurrence = next((item for item in parsed.outgoing_links if item.occurrence_id == occurrence_id), None)
        if occurrence is None or occurrence.link_type not in {"wiki_link", "internal_markdown"}:
            raise KnowledgeContractError("INVALID_LINK_OCCURRENCE", "Link occurrence is no longer valid.")
        documents, _ = self.service.repository.graph_records(source.id)
        target = next((item for item in documents if item.id == target_document_id), None)
        if target is None:
            if "::" in target_document_id and not target_document_id.startswith(f"{source.id}::"):
                raise KnowledgeContractError("CROSS_SOURCE_LINK_NOT_ALLOWED", "Cross-source links are not allowed.")
            raise KnowledgeContractError("LINK_TARGET_NOT_FOUND", "Link target was not found.")
        if target.id == document.id:
            raise KnowledgeContractError("INVALID_LINK_OCCURRENCE", "Self links are not allowed.")
        if link_style not in {"preserve", "wiki", "markdown"}:
            raise KnowledgeContractError("INVALID_LINK_OCCURRENCE", "Unsupported link style.")
        style = occurrence.link_type if link_style == "preserve" else ("wiki_link" if link_style == "wiki" else "internal_markdown")
        label = occurrence.display_text or occurrence.target
        if style == "wiki_link":
            target_path = str(PurePosixPath(target.relative_path).with_suffix(""))
            replacement = f"[[{target_path}|{label}]]"
        else:
            source_dir = posixpath.dirname(document.relative_path)
            relative = posixpath.relpath(target.relative_path, source_dir or ".")
            replacement = f"[{label}]({relative})"
        return occurrence, target, replacement

    def _reindex(self, source: KnowledgeSource, document: GraphDocumentRecord, backup: Path | None) -> dict[str, object]:
        try:
            indexed = self.service.index_file(source.id, document.relative_path, require_capture_write=False)
        except Exception as error:
            return {"fileSaved": True, "backupPath": str(backup) if backup else None, "indexing": {"status": "failed", "errorCode": "INDEX_ERROR", "retryable": True, "message": str(error)}, "graphRevision": self.graph_revision}
        self.graph_revision += 1
        detail = self.service.graphs.get_document_detail(source.id, indexed.document_id, confirm_sensitive=source.sensitive)
        return {"fileSaved": True, "document": {"id": indexed.document_id, "title": indexed.title, "relativePath": indexed.relative_path, "contentHash": detail.content_hash, "modifiedAt": detail.modified_at.isoformat()}, "indexing": {"status": "completed", "documentStatus": indexed.status, "tagCount": indexed.tag_count, "outgoingLinkCount": len(detail.outgoing_documents), "incomingLinkCount": len(detail.incoming_documents), "unresolvedLinkCount": len(detail.unresolved_links)}, "graphRevision": self.graph_revision, "backupPath": str(backup) if backup else None}

    @staticmethod
    def _append_managed_child(body: str, link: str) -> str:
        heading = "## AutoKnowledge 하위 문서"
        section = re.search(r"(?m)^## AutoKnowledge 하위 문서\s*$", body)
        if section is None:
            return f"{body.rstrip()}\n\n{heading}\n\n- {link}\n"
        next_heading = re.search(r"(?m)^#{1,2}\s+", body[section.end() :])
        insertion = (
            section.end() + next_heading.start()
            if next_heading is not None
            else len(body)
        )
        before = body[:insertion].rstrip()
        after = body[insertion:].lstrip("\n")
        suffix = f"\n\n{after}" if after else "\n"
        return f"{before}\n- {link}{suffix}"

    @staticmethod
    def _link_delta(left, right) -> list[str]:
        right_values = {(item.target, item.link_type) for item in right}
        return [item.raw_text for item in left if (item.target, item.link_type) not in right_values]
