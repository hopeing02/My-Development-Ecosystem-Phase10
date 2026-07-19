"""FastAPI entry point for the AutoKnowledge Lite MVP."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from autoknowledge_lite.ai import (
    AnalysisError,
    KnowledgeAnalyzer,
    analyzer_from_environment,
)
from autoknowledge_lite.content import (
    ContentFetcher,
    ContentFetchError,
    HttpContentFetcher,
    should_fetch_content,
)
from autoknowledge_lite.git_sync import GitNoteSync, GitSyncError, NoteSync
from autoknowledge_lite.markdown import MarkdownRenderError, render_markdown
from autoknowledge_lite.models import (
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
from autoknowledge_lite.store import (
    JsonShareStore,
    ShareNotFoundError,
    ShareStoreError,
)

LOGGER = logging.getLogger(__name__)
APP_VERSION = "0.1.0"


def create_app(
    store: JsonShareStore | None = None,
    analyzer: KnowledgeAnalyzer | None = None,
    auto_process: bool | None = None,
    content_fetcher: ContentFetcher | None = None,
    note_store: ObsidianNoteStore | None = None,
    git_sync: NoteSync | None = None,
) -> FastAPI:
    """Create an API application with an injectable persistence boundary."""

    share_store = store or JsonShareStore()
    knowledge_analyzer = analyzer or analyzer_from_environment()
    web_content_fetcher = content_fetcher or HttpContentFetcher()
    obsidian_store = note_store or ObsidianNoteStore()
    note_sync = git_sync or GitNoteSync(obsidian_store.notes_dir.parent)
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

    @application.get("/v1/status", response_model=StatusResponse)
    def get_status() -> StatusResponse:
        return StatusResponse(version=APP_VERSION)

    @application.post(
        "/v1/share",
        response_model=ShareAccepted,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_share(
        request: ShareRequest,
        background_tasks: BackgroundTasks,
    ) -> ShareAccepted:
        received_at = datetime.now(timezone.utc)
        record = ShareRecord(
            job_id=str(uuid4()),
            received_at=received_at,
            content=request.content,
            title=request.title,
            source_url=str(request.source_url) if request.source_url else None,
            shared_at=request.shared_at,
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
        if automatic_processing:
            background_tasks.add_task(auto_process_job, record.job_id)
        return ShareAccepted(
            job_id=record.job_id,
            received_at=record.received_at,
        )

    def auto_process_job(job_id: str) -> None:
        """Analyze and render an accepted job after the API response is sent."""

        try:
            record = enrich_record(share_store.load(job_id))
            analysis = knowledge_analyzer.analyze(record)
            processed_at = datetime.now(timezone.utc)
            processed = record.model_copy(
                update={
                    "status": "processed",
                    "processed_at": processed_at,
                    "analysis": analysis,
                }
            )
            markdown = render_markdown(processed)
            note_path = obsidian_store.save(processed, markdown)
            share_store.update(
                processed.model_copy(
                    update={"markdown": markdown, "note_path": str(note_path)}
                )
            )
            note_sync.sync(note_path)
            LOGGER.info("Automatically processed share job %s", job_id)
        except (
            AnalysisError,
            GitSyncError,
            MarkdownRenderError,
            ObsidianStoreError,
            ShareNotFoundError,
            ShareStoreError,
        ):
            LOGGER.exception("Automatic processing failed for share job %s", job_id)

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
