"""Read-only local HTTP API for Knowledge Plugin graph queries."""

from __future__ import annotations

import asyncio
import logging
import os
from ipaddress import ip_address
from pathlib import Path
from time import perf_counter
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from mde.knowledge.errors import (
    KnowledgeContractError,
    KnowledgeDatabaseError,
    SourceNotFoundError,
)
from mde.knowledge.models import GraphDocumentRecord, KnowledgeSource
from mde.knowledge.command_routes import command_router
from mde.knowledge.document_commands import KnowledgeDocumentCommandService
from mde.knowledge.service import KnowledgeService

API_VERSION = "1"
LOGGER = logging.getLogger(__name__)


def create_app(
    service: KnowledgeService | None = None,
    viewer_dist: Path | None = None,
    android_apk_path: Path | None = None,
) -> FastAPI:
    """Create the local, read-only Knowledge Graph API."""

    knowledge = service or KnowledgeService()
    commands = KnowledgeDocumentCommandService(knowledge)
    application = FastAPI(
        title="MDE Knowledge Graph API",
        version=API_VERSION,
        description="Read-only source-scoped knowledge graph queries.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.middleware("http")
    async def request_metrics(request: Request, call_next):
        started = perf_counter()
        mutating_knowledge = request.url.path.startswith(
            "/api/v1/knowledge/"
        ) and request.method in {"PATCH", "POST"}
        mutating_capture = (
            request.url.path.startswith("/api/v1/capture-relations/")
            and request.method in {"POST", "DELETE"}
        ) or (
            request.url.path.startswith("/api/v1/captures/")
            and request.method == "PATCH"
        )
        if mutating_knowledge or mutating_capture:
            host = (request.url.hostname or "").casefold()
            if not _allowed_command_host(host):
                return _error(403, "INVALID_HOST", "Knowledge commands require a local or private-network host.")
            origin = request.headers.get("origin")
            origin_host = (urlparse(origin).hostname or "").casefold() if origin else ""
            if origin and origin_host != host:
                return _error(403, "INVALID_ORIGIN", "Knowledge command origin is not allowed.")
            if request.method in {"PATCH", "POST"} and request.headers.get("content-type", "").split(";", 1)[0].strip().casefold() != "application/json":
                return _error(415, "INVALID_CONTENT_TYPE", "Knowledge commands require JSON.")
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 2 * 1024 * 1024 + 65536:
                return _error(413, "DOCUMENT_TOO_LARGE", "Knowledge command body is too large.")
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        LOGGER.info(
            "knowledge_api path=%s status=%s elapsed_ms=%.1f",
            request.url.path,
            response.status_code,
            (perf_counter() - started) * 1000,
        )
        return response

    static_root = viewer_dist or _viewer_dist()
    apk_path = android_apk_path or _android_apk()
    if static_root.is_dir() and (static_root / "index.html").is_file():
        assets = static_root / "assets"
        if assets.is_dir():
            application.mount(
                "/assets", StaticFiles(directory=assets), name="viewer-assets"
            )
        icons = static_root / "icons"
        if icons.is_dir():
            application.mount(
                "/icons", StaticFiles(directory=icons), name="viewer-icons"
            )

        @application.get("/", include_in_schema=False)
        async def viewer() -> FileResponse:
            return FileResponse(static_root / "index.html")

        manifest = static_root / "manifest.webmanifest"
        if manifest.is_file():

            @application.get("/manifest.webmanifest", include_in_schema=False)
            async def viewer_manifest() -> FileResponse:
                return FileResponse(manifest, media_type="application/manifest+json")

        service_worker = static_root / "sw.js"
        if service_worker.is_file():

            @application.get("/sw.js", include_in_schema=False)
            async def viewer_service_worker() -> FileResponse:
                return FileResponse(
                    service_worker,
                    media_type="application/javascript",
                    headers={"Service-Worker-Allowed": "/"},
                )

    @application.get("/downloads/mde-knowledge-viewer.apk", include_in_schema=False)
    async def download_android_apk() -> FileResponse:
        if not apk_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Android APK is not available.",
            )
        return FileResponse(
            apk_path,
            media_type="application/vnd.android.package-archive",
            filename="mde-knowledge-viewer-v0.1.0.apk",
            headers={"Cache-Control": "no-store"},
        )

    @application.exception_handler(KnowledgeContractError)
    async def contract_error(
        request: Request, error: KnowledgeContractError
    ) -> JSONResponse:
        del request
        status_code = 404 if error.code.endswith("NOT_FOUND") else 400
        if error.code == "DOCUMENT_CONFLICT":
            status_code = 409
        elif error.code == "DOCUMENT_TOO_LARGE":
            status_code = 413
        elif error.code in {"SOURCE_DISABLED", "SENSITIVE_SOURCE_NOT_ALLOWED", "SOURCE_READ_ONLY", "SOURCE_NOT_EDITABLE", "LINK_REWRITE_NOT_ALLOWED", "PATH_OUTSIDE_SOURCE", "CROSS_SOURCE_LINK_NOT_ALLOWED"}:
            status_code = 403
        elif error.code in {"FILE_WRITE_ERROR", "BACKUP_ERROR", "INDEX_ERROR", "GRAPH_REFRESH_ERROR"}:
            status_code = 500
        return _error(status_code, error.code, str(error), error.details)

    @application.exception_handler(SourceNotFoundError)
    async def source_not_found(
        request: Request, error: SourceNotFoundError
    ) -> JSONResponse:
        del request, error
        return _error(404, "SOURCE_NOT_FOUND", "Knowledge source was not found.")

    @application.exception_handler(KnowledgeDatabaseError)
    async def database_error(
        request: Request, error: KnowledgeDatabaseError
    ) -> JSONResponse:
        del request, error
        return _error(500, "DATABASE_ERROR", "Knowledge database operation failed.")

    @application.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request
        location = {str(item) for detail in error.errors() for item in detail["loc"]}
        if "depth" in location:
            code = "INVALID_DEPTH"
        elif "direction" in location:
            code = "INVALID_DIRECTION"
        elif "limit" in location:
            code = "INVALID_LIMIT"
        else:
            code = "INVALID_QUERY"
        return _error(400, code, "Knowledge API request validation failed.")

    @application.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        LOGGER.error(
            "knowledge_api path=%s error_code=INTERNAL_ERROR error_type=%s",
            request.url.path,
            type(error).__name__,
        )
        return _error(500, "INTERNAL_ERROR", "Unexpected Knowledge API error.")

    @application.get("/api/v1/knowledge/sources")
    async def list_sources() -> JSONResponse:
        sources = []
        for source in knowledge.list_sources():
            _, document_count = knowledge.show_source(source.id)
            payload = _source_payload(source)
            payload["documentCount"] = document_count
            sources.append(payload)
        return _success({"sources": sources})

    @application.get("/api/v1/knowledge/sources/{source_id}/graph")
    async def source_graph(
        source_id: str,
        tag: str | None = None,
        query: str | None = None,
        include_orphans: bool = Query(True, alias="includeOrphans"),
        include_broken: bool = Query(False, alias="includeBroken"),
        limit: int = 1000,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ) -> JSONResponse:
        graph = knowledge.graphs.get_source_graph(
            source_id,
            tag=tag,
            query=query,
            include_orphans=include_orphans,
            include_broken=include_broken,
            limit=limit,
            confirm_sensitive=confirm_sensitive,
        )
        return _success(_graph_payload(graph))

    @application.get(
        "/api/v1/knowledge/sources/{source_id}/documents/{document_id:path}/graph"
    )
    async def document_graph(
        source_id: str,
        document_id: str,
        depth: int = 1,
        direction: str = "both",
        include_broken: bool = Query(False, alias="includeBroken"),
        limit: int = 300,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ) -> JSONResponse:
        graph = knowledge.graphs.get_document_graph(
            source_id,
            document_id,
            depth=depth,
            direction=direction,
            include_broken=include_broken,
            limit=limit,
            confirm_sensitive=confirm_sensitive,
        )
        return _success(_graph_payload(graph))

    @application.get(
        "/api/v1/knowledge/sources/{source_id}/documents/{document_id:path}"
    )
    async def document_detail(
        source_id: str,
        document_id: str,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ) -> JSONResponse:
        detail = knowledge.graphs.get_document_detail(
            source_id, document_id, confirm_sensitive=confirm_sensitive
        )
        return _success(
            {
                "document": {
                    "id": detail.id,
                    "sourceId": detail.source_id,
                    "title": detail.title,
                    "relativePath": detail.relative_path,
                    "category": detail.category,
                    "tags": list(detail.tags),
                    "aliases": list(detail.aliases),
                    "modifiedAt": detail.modified_at,
                    "indexedAt": detail.indexed_at,
                    "preview": detail.preview,
                    "body": detail.body,
                    "rawContent": detail.raw_content,
                    "frontmatter": detail.frontmatter,
                    "contentHash": detail.content_hash,
                    "editable": detail.editable,
                    "outgoingLinks": [
                        {"documentId": item.document_id, "sourceId": item.source_id, "title": item.title}
                        for item in detail.outgoing_documents
                    ],
                    "incomingLinks": [
                        {"documentId": item.document_id, "sourceId": item.source_id, "title": item.title}
                        for item in detail.incoming_documents
                    ],
                    "unresolvedLinks": list(detail.unresolved_links),
                    "ambiguousLinks": list(detail.ambiguous_links),
                    "unresolvedLinkOccurrences": [
                        {
                            "id": item.occurrence_id,
                            "rawText": item.raw_text,
                            "rawTarget": item.raw_target,
                            "target": item.target,
                            "linkType": item.link_type,
                            "startOffset": item.start_offset,
                            "endOffset": item.end_offset,
                            "line": item.line,
                            "column": item.column,
                            "contextPreview": item.context_preview,
                            "resolutionStatus": item.resolution_status,
                        }
                        for item in detail.unresolved_occurrences
                    ],
                }
            }
        )

    @application.get("/api/v1/knowledge/search")
    async def search(
        query: str = Query(..., alias="q"),
        source_id: str | None = Query(None, alias="sourceId"),
        tag: str | None = None,
        limit: int = 20,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ) -> JSONResponse:
        documents = knowledge.graphs.search_documents(
            query,
            source_id=source_id,
            confirm_sensitive=confirm_sensitive,
            tag=tag,
            limit=limit,
        )
        return _success({"documents": [_document_summary(item, query) for item in documents]})

    @application.get("/api/v1/knowledge/sources/{source_id}/tags")
    async def source_tags(
        source_id: str,
        confirm_sensitive: bool = Query(False, alias="confirmSensitive"),
    ) -> JSONResponse:
        tags = knowledge.graphs.get_tags(source_id, confirm_sensitive=confirm_sensitive)
        return _success(
            {
                "tags": [
                    {"name": item.name, "documentCount": item.document_count}
                    for item in tags
                ]
            }
        )

    # The Viewer remains a single-origin application. Capture persistence stays
    # owned by AutoKnowledge Lite on loopback; this narrow gateway exposes only
    # its Viewer/query and relation-management routes.
    @application.api_route(
        "/api/v1/captures{capture_path:path}",
        methods=["GET", "PATCH"],
        response_model=None,
    )
    async def capture_gateway(request: Request, capture_path: str) -> Response:
        return await _proxy_capture_request(request, f"/api/v1/captures{capture_path}")

    @application.api_route(
        "/api/v1/capture-relations/{relation_path:path}",
        methods=["POST", "DELETE"],
        response_model=None,
    )
    async def capture_relation_gateway(request: Request, relation_path: str) -> Response:
        return await _proxy_capture_request(
            request, f"/api/v1/capture-relations/{relation_path}"
        )

    @application.get("/api/v1/graph", response_model=None)
    async def capture_graph_gateway(request: Request) -> Response:
        return await _proxy_capture_request(request, "/api/v1/graph")

    @application.get(
        "/api/v1/graph/neighborhood/{entity_id}", response_model=None
    )
    async def capture_neighborhood_gateway(
        request: Request, entity_id: str
    ) -> Response:
        return await _proxy_capture_request(
            request, f"/api/v1/graph/neighborhood/{entity_id}"
        )

    @application.get("/api/v1/files/history", response_model=None)
    async def capture_file_history_gateway(request: Request) -> Response:
        return await _proxy_capture_request(request, "/api/v1/files/history")

    @application.get(
        "/api/v1/documents/{document_id:path}/capture-backlinks",
        response_model=None,
    )
    async def capture_backlinks_gateway(
        request: Request, document_id: str
    ) -> Response:
        return await _proxy_capture_request(
            request, f"/api/v1/documents/{document_id}/capture-backlinks"
        )

    application.include_router(command_router(commands, _success))
    return application


def _source_payload(source: KnowledgeSource) -> dict[str, object]:
    return {
        "id": source.id,
        "name": source.name,
        "category": source.category,
        "sourceType": source.source_type,
        "sensitive": source.sensitive,
        "enabled": source.enabled,
        "readOnly": source.read_only,
        "editableInViewer": source.editable_in_viewer,
        "allowLinkRewrite": source.allow_link_rewrite,
        "allowDocumentCreate": source.allow_document_create,
        "allowAsSharedLinkTarget": source.allow_as_shared_link_target,
    }


def _graph_payload(graph) -> dict[str, object]:
    return {
        "source": _source_payload(graph.source),
        "nodes": [
            {
                "id": node.id,
                "sourceId": node.source_id,
                "title": node.title,
                "label": node.title,
                "relativePath": node.relative_path,
                "category": node.category,
                "tags": list(node.tags),
                "incomingCount": node.incoming_count,
                "outgoingCount": node.outgoing_count,
                "brokenOutgoingCount": node.broken_outgoing_count,
                "isOrphan": node.is_orphan,
                "modifiedAt": node.modified_at,
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "linkType": edge.link_type,
                "displayText": edge.display_text,
            }
            for edge in graph.edges
        ],
        "brokenEdges": [
            {
                "id": link.id,
                "sourceDocumentId": link.source_document_id,
                "target": link.target,
                "linkType": link.link_type,
                "resolutionStatus": link.resolution_status,
            }
            for link in graph.broken_links
        ],
        "totalDocumentCount": graph.total_document_count,
        "returnedDocumentCount": graph.returned_document_count,
        "truncated": graph.truncated,
    }


def _document_summary(document: GraphDocumentRecord, query: str = "") -> dict[str, object]:
    needle = query.strip().casefold()
    title = document.title.casefold()
    aliases = {item.casefold() for item in document.aliases}
    stem = Path(document.relative_path).stem.casefold()
    path = document.relative_path.casefold()
    if needle and title == needle:
        reason = "exact_title"
    elif needle and needle in aliases:
        reason = "exact_alias"
    elif needle and stem == needle:
        reason = "exact_stem"
    elif needle and needle in title:
        reason = "partial_title"
    elif needle and needle in path:
        reason = "partial_path"
    else:
        reason = "content"
    return {
        "id": document.id,
        "sourceId": document.source_id,
        "title": document.title,
        "relativePath": document.relative_path,
        "category": document.category,
        "tags": list(document.tags),
        "modifiedAt": document.modified_at,
        "snippet": document.content[:160],
        "matchReason": reason,
    }


def _success(data: dict[str, object]) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder({"apiVersion": API_VERSION, "success": True, "data": data})
    )


def _error(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "apiVersion": API_VERSION,
            "success": False,
            "error": {"code": code, "message": message, "details": details or {}},
        },
    )


def _viewer_dist() -> Path:
    configured = os.getenv("MDE_KNOWLEDGE_VIEWER_DIST")
    if configured:
        return Path(configured).resolve()
    packaged = Path(__file__).resolve().parent / "viewer"
    if packaged.is_dir():
        return packaged
    return (Path.cwd() / "apps" / "knowledge-viewer" / "dist").resolve()


def _android_apk() -> Path:
    configured = os.getenv("MDE_KNOWLEDGE_VIEWER_APK")
    if configured:
        return Path(configured).resolve()
    return (
        Path(__file__).resolve().parents[5]
        / "apps"
        / "knowledge-viewer"
        / "android"
        / "app"
        / "build"
        / "outputs"
        / "apk"
        / "debug"
        / "app-debug.apk"
    )


def _allowed_command_host(host: str) -> bool:
    if host in {"localhost", "testserver"}:
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return not (address.is_global or address.is_unspecified or address.is_multicast)


async def _proxy_capture_request(request: Request, path: str) -> Response:
    base = os.getenv("AUTOKNOWLEDGE_CAPTURE_API_URL", "http://127.0.0.1:8000")
    parsed = urlparse(base)
    if parsed.scheme != "http" or (parsed.hostname or "").casefold() not in {
        "127.0.0.1",
        "localhost",
    }:
        return _error(
            503,
            "CAPTURE_SERVICE_UNAVAILABLE",
            "Capture API must use the configured loopback service.",
        )
    body = await request.body()
    query = request.url.query
    target = f"{base.rstrip('/')}{path}{f'?{query}' if query else ''}"
    headers = {"Accept": "application/json"}
    if request.headers.get("content-type"):
        headers["Content-Type"] = request.headers["content-type"]
    if request.headers.get("authorization"):
        headers["Authorization"] = request.headers["authorization"]

    def send() -> tuple[int, bytes, str]:
        outgoing = UrlRequest(
            target,
            data=body if body else None,
            headers=headers,
            method=request.method,
        )
        try:
            with urlopen(outgoing, timeout=10) as response:
                return (
                    response.status,
                    response.read(),
                    response.headers.get_content_type(),
                )
        except HTTPError as error:
            return error.code, error.read(), error.headers.get_content_type()

    try:
        status_code, content, content_type = await asyncio.to_thread(send)
    except (URLError, TimeoutError, OSError):
        return _error(
            503,
            "CAPTURE_SERVICE_UNAVAILABLE",
            "AutoKnowledge Capture service is not available.",
        )
    return Response(
        content=content,
        status_code=status_code,
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )
