"""Local-only HTTP command routes for explicit document edits."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from mde.knowledge.document_commands import DocumentUpdate, KnowledgeDocumentCommandService


class UpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    expected_content_hash: str = Field(alias="expectedContentHash", min_length=1)
    title: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=500)
    aliases: list[str] = Field(default_factory=list, max_length=500)
    body: str
    create_backup: bool = Field(True, alias="createBackup")
    confirm_sensitive: bool = Field(False, alias="confirmSensitive")

    def command(self) -> DocumentUpdate:
        return DocumentUpdate(
            expected_content_hash=self.expected_content_hash,
            title=self.title,
            tags=self.tags,
            aliases=self.aliases,
            body=self.body,
            create_backup=self.create_backup,
        )


class LinkResolutionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    expected_content_hash: str = Field(alias="expectedContentHash", min_length=1)
    link_occurrence_id: str = Field(alias="linkOccurrenceId", min_length=1)
    target_document_id: str = Field(alias="targetDocumentId", min_length=1)
    link_style: str = Field("preserve", alias="linkStyle")
    create_backup: bool = Field(True, alias="createBackup")
    confirm_sensitive: bool = Field(False, alias="confirmSensitive")
    preview_only: bool = Field(False, alias="previewOnly")


def command_router(commands: KnowledgeDocumentCommandService, success) -> APIRouter:
    router = APIRouter(prefix="/api/v1/knowledge")

    @router.post("/sources/{source_id}/documents/{document_id:path}/preview-update")
    async def preview_update(source_id: str, document_id: str, request: UpdateRequest):
        return success({"preview": commands.preview_update(source_id, document_id, request.command(), confirm_sensitive=request.confirm_sensitive)})

    @router.patch("/sources/{source_id}/documents/{document_id:path}")
    async def update_document(source_id: str, document_id: str, request: UpdateRequest):
        return success(commands.update_document(source_id, document_id, request.command(), confirm_sensitive=request.confirm_sensitive))

    @router.post("/sources/{source_id}/documents/{document_id:path}/link-resolutions")
    async def resolve_link(source_id: str, document_id: str, request: LinkResolutionRequest):
        arguments = dict(
            expected_content_hash=request.expected_content_hash,
            occurrence_id=request.link_occurrence_id,
            target_document_id=request.target_document_id,
            link_style=request.link_style,
            confirm_sensitive=request.confirm_sensitive,
        )
        if request.preview_only:
            return success({"preview": commands.preview_link_resolution(source_id, document_id, **arguments)})
        return success(commands.resolve_link(source_id, document_id, create_backup=request.create_backup, **arguments))

    @router.post("/sources/{source_id}/documents/{document_id:path}/reindex")
    async def reindex_document(
        source_id: str,
        document_id: str,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ):
        source = commands.service.registry.get(source_id)
        commands._authorize(source, confirm_sensitive=confirm_sensitive, require_link_rewrite=False)
        documents, _ = commands.service.repository.graph_records(source.id)
        document = next((item for item in documents if item.id == document_id), None)
        if document is None:
            from mde.knowledge.errors import KnowledgeContractError
            raise KnowledgeContractError("DOCUMENT_NOT_FOUND", "Knowledge document was not found.")
        result = commands.service.index_file(source.id, document.relative_path, require_capture_write=False)
        commands.graph_revision += 1
        return success({"indexing": {"status": "completed", "documentStatus": result.status}, "graphRevision": commands.graph_revision})

    return router
