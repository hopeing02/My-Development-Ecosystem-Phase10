"""FastAPI entry point for the AutoKnowledge Lite MVP."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse

from autoknowledge_lite.ai import (
    AnalysisError,
    DeterministicKnowledgeAnalyzer,
    KnowledgeAnalyzer,
    analyzer_from_environment,
)
from autoknowledge_lite.capture_api import (
    CaptureApplicationService,
    CaptureError,
    create_capture_service,
    install_capture_api,
    legacy_share_to_envelope,
)
from autoknowledge_lite.capture_relations import install_relation_api
from autoknowledge_lite.capture_query import (
    CaptureQueryService,
    install_capture_query_api,
)
from autoknowledge_lite.codex_control import CodexController, install_codex_control_api
from autoknowledge_lite.chatgpt_import import ChatGPTImportService
from autoknowledge_lite.chatgpt_import_api import install_chatgpt_import_api
from autoknowledge_lite.chatgpt_shared_import import ChatGPTSharedImportService
from autoknowledge_lite.chatgpt_shared_import_api import (
    install_chatgpt_shared_import_api,
)
from autoknowledge_lite.chatgpt_query import (
    ChatGPTQueryService,
    install_chatgpt_query_api,
)
from autoknowledge_lite.content import (
    ContentFetcher,
    ContentFetchError,
    HttpContentFetcher,
    should_fetch_content,
)
from autoknowledge_lite.git_sync import GitNoteSync, GitSyncError, NoteSync
from autoknowledge_lite.markdown import MarkdownRenderError, render_markdown
from autoknowledge_lite.mde_client import MDEClientError, MDEKnowledgeClient
from autoknowledge_lite.models import (
    KnowledgeAnalysis,
    MarkdownRequest,
    MarkdownResult,
    ProcessedShare,
    ProcessRequest,
    ShareAccepted,
    ShareRecord,
    ShareRequest,
    StatusResponse,
)
from autoknowledge_lite.obsidian import ObsidianNoteStore, ObsidianStoreError
from autoknowledge_lite.pc_ui import PC_CAPTURE_HTML
from autoknowledge_lite.store import (
    JsonShareStore,
    ShareNotFoundError,
    ShareStoreError,
)

LOGGER = logging.getLogger(__name__)
APP_VERSION = "0.2.4"
ANDROID_APK_PATH = (
    Path(__file__).resolve().parents[2]
    / "android"
    / "app"
    / "build"
    / "outputs"
    / "apk"
    / "debug"
    / "app-debug.apk"
)


class KnowledgeIndexer(Protocol):
    """Index one Vault-relative Markdown file through the MDE contract."""

    def index_file(self, source: str, relative_path: str) -> dict[str, Any]: ...

    def search_documents(
        self, source: str, query: str, *, limit: int = 20
    ) -> tuple[Any, ...]: ...

    def link_child(
        self, source: str, parent_document_id: str, target_document_id: str
    ) -> dict[str, Any]: ...


def create_app(
    store: JsonShareStore | None = None,
    analyzer: KnowledgeAnalyzer | None = None,
    auto_process: bool | None = None,
    content_fetcher: ContentFetcher | None = None,
    note_store: ObsidianNoteStore | None = None,
    git_sync: NoteSync | None = None,
    mde_client: KnowledgeIndexer | None = None,
    android_apk_path: Path | None = None,
    capture_service: CaptureApplicationService | None = None,
    codex_controller: CodexController | None = None,
    chatgpt_import_service: ChatGPTImportService | None = None,
    chatgpt_shared_import_service: ChatGPTSharedImportService | None = None,
) -> FastAPI:
    """Create an API application with an injectable persistence boundary."""

    share_store = store or JsonShareStore()
    knowledge_analyzer = analyzer or analyzer_from_environment()
    web_content_fetcher = content_fetcher or HttpContentFetcher()
    obsidian_store = note_store or ObsidianNoteStore()
    note_sync = git_sync or GitNoteSync(obsidian_store.vault_dir)
    knowledge_indexer = mde_client or MDEKnowledgeClient()
    knowledge_source = (
        os.getenv("AUTOKNOWLEDGE_MDE_SOURCE", "autoknowledge-vault").strip()
        or "autoknowledge-vault"
    )
    fallback_analyzer = DeterministicKnowledgeAnalyzer()
    index_lock = Lock()
    apk_path = android_apk_path or ANDROID_APK_PATH
    automatic_processing = (
        _environment_flag("AUTOKNOWLEDGE_AUTO_PROCESS", default=True)
        if auto_process is None
        else auto_process
    )
    application = FastAPI(
        title="AutoKnowledge Lite",
        version=APP_VERSION,
        description="Capture shared content for the AutoKnowledge workflow.",
    )
    unified_capture_service = capture_service or create_capture_service(
        obsidian_store.vault_dir,
        share_store.root,
        indexer=knowledge_indexer,
        knowledge_source=knowledge_source,
    )
    chatgpt_query_service = ChatGPTQueryService(share_store.root)
    install_capture_api(application, unified_capture_service)
    if unified_capture_service.relation_service is not None:
        install_relation_api(application, unified_capture_service.relation_service)
        install_capture_query_api(
            application,
            CaptureQueryService(
                unified_capture_service.relation_service.repository,
                graph_provider=chatgpt_query_service,
            ),
        )
    install_codex_control_api(application, codex_controller)
    install_chatgpt_import_api(
        application,
        chatgpt_import_service or ChatGPTImportService(share_store.root),
    )
    install_chatgpt_shared_import_api(
        application,
        chatgpt_shared_import_service or ChatGPTSharedImportService(share_store.root),
    )
    install_chatgpt_query_api(application, chatgpt_query_service)

    @application.get("/v1/status", response_model=StatusResponse)
    async def get_status() -> StatusResponse:
        return StatusResponse(version=APP_VERSION)

    @application.get("/pc", response_class=HTMLResponse)
    async def get_pc_capture_page() -> str:
        return PC_CAPTURE_HTML

    @application.get("/v1/knowledge/documents")
    def search_parent_documents(
        query: str = Query(..., alias="q", min_length=1, max_length=200),
        limit: int = Query(20, ge=1, le=50),
    ) -> dict[str, object]:
        try:
            documents = knowledge_indexer.search_documents(
                knowledge_source, query.strip(), limit=limit
            )
        except MDEClientError as error:
            LOGGER.exception("MDE parent document search failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Knowledge document search is unavailable.",
            ) from error
        return {
            "documents": [
                {
                    "id": item.id,
                    "source_id": item.source_id,
                    "title": item.title,
                    "relative_path": item.relative_path,
                    "snippet": item.snippet,
                }
                for item in documents
            ]
        }

    @application.get("/downloads/autoknowledge-lite.apk")
    def download_android_apk() -> FileResponse:
        if not apk_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Android APK is not available.",
            )
        return FileResponse(
            apk_path,
            media_type="application/vnd.android.package-archive",
            filename=f"autoknowledge-lite-v{APP_VERSION}.apk",
        )

    @application.post(
        "/v1/share",
        response_model=ShareAccepted,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def create_share(
        request: ShareRequest,
        background_tasks: BackgroundTasks,
    ) -> ShareAccepted:
        received_at = datetime.now(timezone.utc)
        job_id = str(uuid4())
        parent_document_id = request.parent_document_id
        if (
            request.capture_origin in {"pc_clipboard", "android_clipboard"}
            and parent_document_id is None
        ):
            previous = share_store.latest_saved(capture_origin=request.capture_origin)
            parent_document_id = previous.document_id if previous else None
        capture_result = None
        if request.capture_origin == "android_clipboard" and request.source_type:
            try:
                capture_result = unified_capture_service.capture(
                    legacy_share_to_envelope(request, job_id)
                )
            except CaptureError as error:
                raise HTTPException(
                    status_code=error.http_status,
                    detail={
                        "code": error.code,
                        "message": error.message,
                        "field": error.field,
                    },
                ) from error
        record = ShareRecord(
            job_id=job_id,
            received_at=received_at,
            content=request.content,
            title=request.title,
            source_url=str(request.source_url) if request.source_url else None,
            shared_at=request.shared_at,
            target_folder=request.target_folder,
            capture_origin=request.capture_origin,
            parent_document_id=parent_document_id,
            source_type=request.source_type,
            source_app=request.source_app,
            content_hash=request.content_hash,
            captured_at=request.captured_at,
            device_id=request.device_id,
            document_id=capture_result.document_id if capture_result else None,
            note_path=capture_result.document_path if capture_result else None,
        )
        try:
            share_store.save(record)
        except ShareStoreError as error:
            LOGGER.exception("Failed to persist share job %s", record.job_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to accept shared content.",
            ) from error
        LOGGER.info("Accepted share job %s", record.job_id)
        if automatic_processing and capture_result is None:
            background_tasks.add_task(auto_process_job, record.job_id)
        return ShareAccepted(
            job_id=record.job_id,
            received_at=record.received_at,
        )

    def auto_process_job(job_id: str) -> None:
        """Analyze and render an accepted job after the API response is sent."""

        try:
            record = enrich_record(share_store.load(job_id))
            local_analysis = fallback_analyzer.analyze(record)
            persist_processed_note(record, local_analysis)
            if (
                getattr(knowledge_analyzer, "provider", None)
                == fallback_analyzer.provider
            ):
                LOGGER.info("Automatically processed share job %s", job_id)
                return
            try:
                analysis = knowledge_analyzer.analyze(record)
            except AnalysisError:
                LOGGER.exception(
                    "Configured analysis failed for share job %s; keeping local result",
                    job_id,
                )
                return
            persist_processed_note(record, analysis)
            LOGGER.info("Automatically processed share job %s", job_id)
        except (
            AnalysisError,
            MarkdownRenderError,
            ObsidianStoreError,
            ShareNotFoundError,
            ShareStoreError,
        ):
            LOGGER.exception("Automatic processing failed for share job %s", job_id)

    def persist_processed_note(
        record: ShareRecord,
        analysis: KnowledgeAnalysis,
    ) -> ShareRecord:
        """Persist, index, and synchronize one analyzed note."""

        processed = record.model_copy(
            update={
                "status": "processed",
                "processed_at": datetime.now(timezone.utc),
                "analysis": analysis,
            }
        )
        markdown = render_markdown(processed)
        note_path = obsidian_store.save(processed, markdown)
        indexed = index_note(note_path)
        document_id = (
            str(indexed["documentId"])
            if indexed and indexed.get("documentId")
            else None
        )
        saved = processed.model_copy(
            update={
                "markdown": markdown,
                "note_path": str(note_path),
                "document_id": document_id,
            }
        )
        share_store.update(saved)
        if saved.parent_document_id and saved.document_id:
            try:
                knowledge_indexer.link_child(
                    knowledge_source,
                    saved.parent_document_id,
                    saved.document_id,
                )
            except MDEClientError:
                LOGGER.exception(
                    "Unable to link parent %s to note %s",
                    saved.parent_document_id,
                    saved.document_id,
                )
        try:
            note_sync.sync(note_path)
        except GitSyncError:
            LOGGER.exception(
                "Git synchronization failed for share job %s", record.job_id
            )
        return saved

    def index_note(note_path: Path) -> dict[str, Any] | None:
        """Index a saved note without rolling back the durable Markdown file."""

        try:
            relative_path = note_path.resolve().relative_to(
                obsidian_store.vault_dir.resolve()
            )
            with index_lock:
                return knowledge_indexer.index_file(
                    knowledge_source,
                    relative_path.as_posix(),
                )
        except (MDEClientError, OSError, ValueError):
            LOGGER.exception("MDE indexing failed for note %s", note_path.name)
            return None

    def enrich_record(record: ShareRecord) -> ShareRecord:
        if not should_fetch_content(record):
            return record
        try:
            content = web_content_fetcher.fetch(record.source_url or "")
        except ContentFetchError:
            LOGGER.exception(
                "Unable to fetch source content for share job %s", record.job_id
            )
            return record
        enriched = record.model_copy(update={"content": content})
        share_store.update(enriched)
        return enriched

    @application.post("/v1/ai/process", response_model=ProcessedShare)
    def process_share(request: ProcessRequest) -> ProcessedShare:
        job_id = str(request.job_id)
        try:
            record = enrich_record(share_store.load(job_id))
        except ShareNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share job not found.",
            ) from error
        except ShareStoreError as error:
            LOGGER.exception("Failed to load share job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to load shared content.",
            ) from error

        try:
            analysis = knowledge_analyzer.analyze(record)
        except AnalysisError as error:
            LOGGER.exception("Analysis failed for share job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to analyze shared content.",
            ) from error

        processed_at = datetime.now(timezone.utc)
        processed = record.model_copy(
            update={
                "status": "processed",
                "processed_at": processed_at,
                "analysis": analysis,
            }
        )
        try:
            share_store.update(processed)
        except ShareStoreError as error:
            LOGGER.exception("Failed to update share job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to save analysis result.",
            ) from error
        return ProcessedShare(
            job_id=processed.job_id,
            processed_at=processed_at,
            analysis=analysis,
        )

    @application.post("/v1/markdown", response_model=MarkdownResult)
    def create_markdown(request: MarkdownRequest) -> MarkdownResult:
        job_id = str(request.job_id)
        try:
            record = share_store.load(job_id)
        except ShareNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Share job not found.",
            ) from error
        except ShareStoreError as error:
            LOGGER.exception("Failed to load share job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to load shared content.",
            ) from error

        try:
            markdown = render_markdown(record)
        except MarkdownRenderError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Share job must be analyzed first.",
            ) from error

        try:
            note_path = obsidian_store.save(record, markdown)
            share_store.update(
                record.model_copy(
                    update={"markdown": markdown, "note_path": str(note_path)}
                )
            )
        except (ObsidianStoreError, ShareStoreError) as error:
            LOGGER.exception("Failed to save Markdown for share job %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to save Markdown document.",
            ) from error
        try:
            note_sync.sync(note_path)
        except GitSyncError:
            LOGGER.exception("Git synchronization failed for share job %s", job_id)
        index_note(note_path)
        return MarkdownResult(
            job_id=job_id,
            markdown=markdown,
            note_path=str(note_path),
        )

    return application


def _environment_flag(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


app = create_app()
