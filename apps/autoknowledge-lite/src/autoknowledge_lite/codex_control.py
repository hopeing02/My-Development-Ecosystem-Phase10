"""Authenticated, least-privilege mobile control surface for Codex capture."""

from __future__ import annotations

import hmac
import os
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


class CodexController(Protocol):
    def list_projects(self) -> list[dict[str, Any]]: ...
    def discover_codex_sessions(self) -> list[dict[str, Any]]: ...
    def inspect_codex_session(self, source_session_id: str) -> dict[str, Any]: ...
    def start(
        self, project_id: str, title: str, request: str | None = None
    ) -> dict[str, Any]: ...
    def attach_codex_session(
        self,
        capture_session_id: str,
        source_session_id: str,
        *,
        consent: bool,
        client_type: str = "codex_app_server",
    ) -> dict[str, Any]: ...
    def sync_codex_session(
        self, capture_session_id: str, *, transmit: bool = True
    ) -> dict[str, Any]: ...
    def finalize(
        self,
        *,
        session_id: str | None = None,
        summary: str | None = None,
        closure_reason: str = "manual_finalize",
        transmit: bool = True,
    ) -> dict[str, Any]: ...
    def load_session(self, session_id: str) -> dict[str, Any]: ...
    def doctor(self) -> list[dict[str, Any]]: ...


class StartCaptureRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    project_id: str = Field(alias="projectId", min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)


class AttachRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    source_session_id: str = Field(
        alias="sourceSessionId", min_length=1, max_length=200
    )
    consent: bool


class SyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transmit: bool = True


class FinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str | None = Field(default=None, max_length=1000)
    transmit: bool = True


def default_controller() -> CodexController:
    from mde.codex_capture.service import CodexCaptureService

    return CodexCaptureService()


def install_codex_control_api(
    application: FastAPI, controller: CodexController | None = None
) -> None:
    def invoke(action: Any) -> Any | JSONResponse:
        try:
            return action(_controller(controller))
        except (
            Exception
        ) as error:  # noqa: BLE001 - controller errors become safe codes.
            code = str(getattr(error, "code", "CODEX_CONTROL_FAILED"))
            http_status = (
                404 if code in {"SESSION_NOT_FOUND", "PROJECT_NOT_REGISTERED"} else 409
            )
            if code in {
                "CODEX_APP_SERVER_NOT_FOUND",
                "CODEX_APP_SERVER_UNAVAILABLE",
                "SERVER_UNREACHABLE",
            }:
                http_status = 503
            return JSONResponse(
                status_code=http_status,
                content={"error": {"code": code, "message": _safe_message(code)}},
            )

    @application.get("/api/v1/mobile/status", response_model=None)
    def mobile_status(request: Request) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        result = invoke(lambda service: service.doctor())
        if isinstance(result, JSONResponse):
            return result
        return {
            "status": "connected",
            "codexCaptureEnabled": _capture_enabled(),
            "checks": [_safe_check(item) for item in result],
        }

    @application.get("/api/v1/mobile/codex/projects", response_model=None)
    def projects(request: Request) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        result = invoke(lambda service: service.list_projects())
        if isinstance(result, JSONResponse):
            return result
        return {
            "projects": [
                {
                    "projectId": item.get("projectId"),
                    "displayName": item.get("displayName"),
                    "enabled": bool(item.get("enabled", True)),
                }
                for item in result
            ]
        }

    @application.get("/api/v1/mobile/codex/sessions", response_model=None)
    def sessions(
        request: Request,
        limit: int = Query(20, ge=1, le=50),
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response

        def discover(service: CodexController) -> list[dict[str, Any]]:
            # Keep discovery to one app-server request. Reading every thread here
            # made the mobile list perform an N+1 sequence of subprocess calls and
            # routinely exceed the Android HTTP timeout. Full details are loaded
            # only after the user selects a session.
            return [
                _safe_discovered(item)
                for item in service.discover_codex_sessions()[:limit]
            ]

        result = invoke(discover)
        if isinstance(result, JSONResponse):
            return result
        return {"sessions": result}

    @application.get(
        "/api/v1/mobile/codex/sessions/{source_session_id}", response_model=None
    )
    def inspect(
        source_session_id: str, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        return invoke(lambda service: service.inspect_codex_session(source_session_id))

    @application.post("/api/v1/mobile/codex/captures", response_model=None)
    def start_capture(
        payload: StartCaptureRequest, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        result = invoke(
            lambda service: service.start(payload.project_id, payload.title)
        )
        return _safe_capture(result) if isinstance(result, dict) else result

    @application.post(
        "/api/v1/mobile/codex/captures/{capture_session_id}/attach", response_model=None
    )
    def attach(
        capture_session_id: str, payload: AttachRequest, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        if not payload.consent:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "CODEX_CONVERSATION_CONSENT_REQUIRED",
                        "message": "Explicit consent is required.",
                    }
                },
            )
        result = invoke(
            lambda service: service.attach_codex_session(
                capture_session_id, payload.source_session_id, consent=True
            )
        )
        if isinstance(result, JSONResponse):
            return result
        return {
            "captureSessionId": capture_session_id,
            "sourceSessionId": result.get("sourceSessionId"),
            "attached": True,
        }

    @application.post(
        "/api/v1/mobile/codex/captures/{capture_session_id}/sync", response_model=None
    )
    def sync(
        capture_session_id: str, payload: SyncRequest, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response

        def synchronize(service: CodexController) -> dict[str, Any]:
            sync_result = service.sync_codex_session(
                capture_session_id, transmit=payload.transmit
            )
            status_result = _safe_capture(service.load_session(capture_session_id))
            status_result.update(
                {
                    "newMessages": sync_result.get("newMessages", 0),
                    "totalMessages": sync_result.get(
                        "totalMessages", status_result["messageCount"]
                    ),
                    "transmitted": sync_result.get("transmitted", False),
                }
            )
            return status_result

        return invoke(synchronize)

    @application.post(
        "/api/v1/mobile/codex/captures/{capture_session_id}/finalize",
        response_model=None,
    )
    def finalize(
        capture_session_id: str, payload: FinalizeRequest, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        result = invoke(
            lambda service: service.finalize(
                session_id=capture_session_id,
                summary=payload.summary,
                closure_reason="mobile_finalize",
                transmit=payload.transmit,
            )
        )
        return _safe_capture(result) if isinstance(result, dict) else result

    @application.get(
        "/api/v1/mobile/codex/captures/{capture_session_id}", response_model=None
    )
    def capture_status(
        capture_session_id: str, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize(request):
            return response
        result = invoke(lambda service: service.load_session(capture_session_id))
        return _safe_capture(result) if isinstance(result, dict) else result


def _controller(injected: CodexController | None) -> CodexController:
    if not _capture_enabled():
        error = RuntimeError("Codex conversation capture is disabled")
        error.code = "CODEX_CONVERSATION_CAPTURE_DISABLED"  # type: ignore[attr-defined]
        raise error
    return injected or default_controller()


def _authorize(request: Request) -> JSONResponse | None:
    configured = os.getenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "").strip()
    if not configured:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "CONTROL_API_DISABLED",
                    "message": "Mobile control API is not configured.",
                }
            },
        )
    if not hmac.compare_digest(
        request.headers.get("Authorization", ""), f"Bearer {configured}"
    ):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication is required.",
                }
            },
        )
    return None


def _capture_enabled() -> bool:
    return os.getenv("MDE_CODEX_CONVERSATION_CAPTURE", "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _safe_discovered(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in (
            "sourceSessionId",
            "clientType",
            "title",
            "createdAt",
            "updatedAt",
            "status",
            "captureSessionCandidate",
        )
        if item.get(key) is not None
    }


def _safe_capture(item: dict[str, Any]) -> dict[str, Any]:
    server = item.get("serverResult") or {}
    result = {
        key: item.get(key)
        for key in (
            "captureSessionId",
            "sourceSessionId",
            "sourceClientType",
            "state",
            "startedAt",
            "endedAt",
            "lastConversationSyncAt",
            "conversationParseStatus",
        )
        if item.get(key) is not None
    }
    result.update(
        {
            "messageCount": len(item.get("messages", [])),
            "revision": server.get("revision"),
            "documentId": server.get("documentId"),
            "documentPath": server.get("documentPath"),
            "viewerUrl": _viewer_document_url(server.get("documentId")),
        }
    )
    return result


def _safe_check(item: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item.get(key)
        for key in ("name", "status", "code", "message")
        if item.get(key) is not None
    }


def _viewer_url() -> str | None:
    value = os.getenv("AUTOKNOWLEDGE_VIEWER_URL", "").strip()
    if not value:
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _viewer_document_url(document_id: Any) -> str | None:
    base = _viewer_url()
    if not base or not document_id:
        return base
    source_id = (
        os.getenv("AUTOKNOWLEDGE_MDE_SOURCE", "autoknowledge-vault").strip()
        or "autoknowledge-vault"
    )
    return (
        f"{base}/?sourceId={quote(source_id, safe='')}"
        f"&documentId={quote(str(document_id), safe='')}"
    )


def _safe_message(code: str) -> str:
    messages = {
        "CODEX_CONVERSATION_CAPTURE_DISABLED": (
            "Codex conversation capture is disabled."
        ),
        "CODEX_CONVERSATION_CONSENT_REQUIRED": "Explicit consent is required.",
        "SESSION_NOT_FOUND": "Capture session was not found.",
        "PROJECT_NOT_REGISTERED": "The selected project is not registered.",
        "CODEX_APP_SERVER_NOT_FOUND": "Codex is not available on the PC.",
        "CODEX_APP_SERVER_UNAVAILABLE": "Codex is not available on the PC.",
        "SERVER_UNREACHABLE": "Capture storage API is unavailable.",
    }
    return messages.get(code, "The Codex capture operation failed.")
