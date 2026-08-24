"""Authenticated API for explicit ChatGPT shared-link imports."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from autoknowledge_lite.chatgpt_import_api import (
    authorize_control_request,
    chatgpt_import_result_payload,
)
from autoknowledge_lite.chatgpt_shared_archive import (
    ChatGPTSharedArchiveError,
    ChatGPTSharedFetchError,
)
from autoknowledge_lite.chatgpt_shared_import import ChatGPTSharedImportService
from autoknowledge_lite.chatgpt_shared_link_source import ChatGPTSharedLinkSourceError

MAX_REQUEST_BYTES = 4096
MAX_URL_LENGTH = 500


def install_chatgpt_shared_import_api(
    application: FastAPI, service: ChatGPTSharedImportService
) -> None:
    @application.post("/api/v1/chatgpt/shared-imports", response_model=None)
    async def import_chatgpt_shared_link(
        request: Request,
    ) -> dict[str, Any] | JSONResponse:
        if response := authorize_control_request(request):
            return response
        content_type = request.headers.get("content-type", "").split(";", 1)[0]
        if content_type != "application/json":
            raise _request_error(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                "CHATGPT_SHARED_REQUEST_CONTENT_TYPE_UNSUPPORTED",
                "Shared-link import requires a JSON request.",
            )
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > MAX_REQUEST_BYTES:
            raise _request_too_large()
        body = await request.body()
        if len(body) > MAX_REQUEST_BYTES:
            raise _request_too_large()
        shared_url = _shared_url(body)
        try:
            result = service.import_shared_link(shared_url)
            return chatgpt_import_result_payload(result)
        except ChatGPTSharedFetchError as error:
            if error.code == "CHATGPT_SHARED_SNAPSHOT_TOO_LARGE":
                response_status = status.HTTP_413_CONTENT_TOO_LARGE
            elif error.code == "CHATGPT_SHARED_CONTENT_TYPE_UNSUPPORTED":
                response_status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            elif error.code in {
                "CHATGPT_SHARED_URL_INVALID",
                "CHATGPT_SHARED_REDIRECT_REJECTED",
                "CHATGPT_SHARED_REDIRECT_INVALID",
                "CHATGPT_SHARED_REDIRECT_LIMIT",
            }:
                response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            else:
                response_status = status.HTTP_502_BAD_GATEWAY
            raise _request_error(response_status, error.code, str(error)) from error
        except ChatGPTSharedArchiveError as error:
            response_status = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if error.code.endswith(("WRITE_FAILED", "INVALID"))
                else status.HTTP_409_CONFLICT
            )
            raise _request_error(response_status, error.code, str(error)) from error
        except ChatGPTSharedLinkSourceError as error:
            raise _request_error(
                status.HTTP_409_CONFLICT, error.code, str(error)
            ) from error


def _shared_url(body: bytes) -> str:
    try:
        payload = json.loads(body)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise _request_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "CHATGPT_SHARED_REQUEST_INVALID",
            "Shared-link import request is invalid.",
        ) from error
    if not isinstance(payload, dict):
        raise _request_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "CHATGPT_SHARED_REQUEST_INVALID",
            "Shared-link import request is invalid.",
        )
    shared_url = payload.get("url")
    if (
        not isinstance(shared_url, str)
        or not shared_url.strip()
        or len(shared_url) > MAX_URL_LENGTH
    ):
        raise _request_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "CHATGPT_SHARED_URL_REQUIRED",
            "A valid ChatGPT shared-link URL is required.",
        )
    return shared_url.strip()


def _request_too_large() -> HTTPException:
    return _request_error(
        status.HTTP_413_CONTENT_TOO_LARGE,
        "CHATGPT_SHARED_REQUEST_TOO_LARGE",
        "Shared-link import request exceeds the size limit.",
    )


def _request_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
