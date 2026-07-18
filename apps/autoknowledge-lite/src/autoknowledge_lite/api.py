"""FastAPI entry point for the AutoKnowledge Lite MVP."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from autoknowledge_lite.ai import (
    AnalysisError,
    KnowledgeAnalyzer,
    analyzer_from_environment,
)
from autoknowledge_lite.models import (
    ProcessedShare,
    ProcessRequest,
    ShareAccepted,
    ShareRecord,
    ShareRequest,
    StatusResponse,
)
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
) -> FastAPI:
    """Create an API application with an injectable persistence boundary."""

    share_store = store or JsonShareStore()
    knowledge_analyzer = analyzer or analyzer_from_environment()
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
    def create_share(request: ShareRequest) -> ShareAccepted:
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
        return ShareAccepted(
            job_id=record.job_id,
            received_at=record.received_at,
        )

    @application.post("/v1/ai/process", response_model=ProcessedShare)
    def process_share(request: ProcessRequest) -> ProcessedShare:
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

    return application


app = create_app()
