"""Authenticated streaming API for explicit ChatGPT export imports."""

from __future__ import annotations

import hmac
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from autoknowledge_lite.chatgpt_archive import ChatGPTArchiveError
from autoknowledge_lite.chatgpt_import import ChatGPTImportError, ChatGPTImportService
from autoknowledge_lite.chatgpt_session_source import (
    DEFAULT_MAX_ARCHIVE_BYTES,
    ChatGPTSessionSourceError,
)

SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


def install_chatgpt_import_api(
    application: FastAPI,
    service: ChatGPTImportService,
    *,
    max_upload_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
) -> None:
    """Install the ChatGPT import endpoint without multipart dependencies."""

    @application.post("/api/v1/chatgpt/imports", response_model=None)
    async def import_chatgpt_export(request: Request) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
        if content_type not in {"application/zip", "application/octet-stream"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "code": "CHATGPT_IMPORT_CONTENT_TYPE_UNSUPPORTED",
                    "message": "ChatGPT export upload must be a ZIP body.",
                },
            )
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > max_upload_bytes:
                raise _too_large()

        incoming_root = service.data_dir / "incoming" / "chatgpt"
        incoming_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        stage = Path(tempfile.mkdtemp(prefix=".upload-", dir=incoming_root))
        upload_path = stage / _upload_filename(
            request.headers.get("x-file-name", "chatgpt-export.zip")
        )
        try:
            size = 0
            with upload_path.open("xb") as target:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > max_upload_bytes:
                        raise _too_large()
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            upload_path.chmod(0o600)
            result = service.import_export(upload_path)
            return {
                "status": (
                    "partial"
                    if result.failed_sessions
                    else (
                        "duplicate"
                        if result.raw_duplicate and not result.projected_sessions
                        else "imported"
                    )
                ),
                "importId": result.import_id,
                "rawDuplicate": result.raw_duplicate,
                "discoveredSessions": result.discovered_sessions,
                "projectedSessions": result.projected_sessions,
                "duplicateSessions": result.duplicate_sessions,
                "failedSessions": result.failed_sessions,
                "warnings": [
                    {
                        "code": issue.code,
                        "sessionId": issue.session_id,
                        "sourceMember": issue.source_member,
                        "sourceIndex": issue.source_index,
                    }
                    for issue in result.issues
                ],
            }
        except ChatGPTSessionSourceError as error:
            raise HTTPException(
                status_code=(
                    status.HTTP_413_CONTENT_TOO_LARGE
                    if "TOO_LARGE" in error.code
                    else status.HTTP_422_UNPROCESSABLE_CONTENT
                ),
                detail={"code": error.code, "message": str(error)},
            ) from error
        except ChatGPTArchiveError as error:
            raise HTTPException(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if error.code.endswith(("WRITE_FAILED", "UNREADABLE"))
                    else status.HTTP_409_CONFLICT
                ),
                detail={"code": error.code, "message": str(error)},
            ) from error
        except ChatGPTImportError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": error.code, "message": str(error)},
            ) from error
        finally:
            _remove_stage(stage, incoming_root)


def _authorize(request: Request) -> JSONResponse | None:
    configured = os.getenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "").strip()
    if not configured:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "CHATGPT_IMPORT_API_DISABLED",
                    "message": "ChatGPT import API is not configured.",
                }
            },
        )
    if not hmac.compare_digest(
        request.headers.get("Authorization", ""), f"Bearer {configured}"
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication is required.",
                }
            },
        )
    return None


def _upload_filename(value: str) -> str:
    filename = Path(value.replace("\\", "/")).name
    sanitized = SAFE_FILENAME.sub("-", filename).strip(".-")
    if not sanitized.casefold().endswith(".zip"):
        return "chatgpt-export.zip"
    return sanitized[:120] or "chatgpt-export.zip"


def _too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail={
            "code": "CHATGPT_IMPORT_UPLOAD_TOO_LARGE",
            "message": "ChatGPT export upload exceeds the size limit.",
        },
    )


def _remove_stage(stage: Path, incoming_root: Path) -> None:
    try:
        resolved = stage.resolve()
        resolved.relative_to(incoming_root.resolve())
    except (OSError, ValueError):
        return
    shutil.rmtree(resolved, ignore_errors=True)
