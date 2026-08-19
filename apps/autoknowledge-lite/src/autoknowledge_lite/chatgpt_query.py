"""Read-only Viewer queries over persisted ChatGPT knowledge projections."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from autoknowledge_lite.chatgpt_import import (
    ChatGPTImportError,
    ChatGPTProjectionRevision,
    ChatGPTProjectionStore,
)
from autoknowledge_lite.knowledge_model import Activity, Message, Provenance, Task
from autoknowledge_lite.task_analyzer import (
    SessionTaskAnalyzer,
    TaskAnalysis,
    TaskBoundaryCandidate,
)

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100
MAX_GRAPH_NODES = 300


class ChatGPTQueryError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class ChatGPTQueryService:
    """Expose only safe latest Session and Message projection fields."""

    def __init__(
        self,
        data_dir: Path,
        *,
        projection_store: ChatGPTProjectionStore | None = None,
        task_analyzer: SessionTaskAnalyzer | None = None,
    ) -> None:
        self.projection_store = projection_store or ChatGPTProjectionStore(data_dir)
        self.task_analyzer = task_analyzer or SessionTaskAnalyzer()

    def list_sessions(
        self,
        *,
        query: str | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        revisions = list(self._latest_revisions())
        if query and query.strip():
            needle = query.strip().casefold()
            revisions = [
                item
                for item in revisions
                if needle in item.projection.session.title.casefold()
                or any(
                    needle in message.content.casefold()
                    for message in item.projection.messages
                )
            ]
        offset = _decode_cursor(cursor)
        page = revisions[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "items": [self._summary(item) for item in page],
            "nextCursor": (
                _encode_cursor(next_offset) if next_offset < len(revisions) else None
            ),
            "hasMore": next_offset < len(revisions),
            "total": len(revisions),
        }

    def detail(self, session_id: str) -> dict[str, Any]:
        revision = self._latest(session_id)
        session = revision.projection.session
        analysis = self._analysis(revision)
        return {
            "session": self._summary(revision)
            | {
                "sourceSessionId": session.source_session_id,
                "taskIds": [task.task_id for task in analysis.tasks],
                "provenance": _provenance(session.provenance),
            },
            "warnings": list(revision.projection.warnings),
            "analysisWarnings": list(analysis.warnings),
            "boundaryCandidates": [
                _boundary_candidate(item) for item in analysis.boundary_candidates
            ],
        }

    def list_tasks(
        self,
        *,
        session_id: str | None = None,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        revisions = (
            (self._latest(session_id),)
            if session_id is not None
            else self._latest_revisions()
        )
        values = [
            task for revision in revisions for task in self._analysis(revision).tasks
        ]
        offset = _decode_cursor(cursor)
        page = values[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "items": [_task(item) for item in page],
            "nextCursor": (
                _encode_cursor(next_offset) if next_offset < len(values) else None
            ),
            "hasMore": next_offset < len(values),
            "total": len(values),
        }

    def task_detail(self, task_id: str) -> dict[str, Any]:
        for revision in self._latest_revisions():
            analysis = self._analysis(revision)
            for task in analysis.tasks:
                if task.task_id != task_id:
                    continue
                return {
                    "task": _task(task),
                    "activities": [
                        _activity(item)
                        for item in analysis.activities
                        if item.task_id == task_id
                    ],
                    "boundaryCandidates": [
                        _boundary_candidate(item)
                        for item in analysis.boundary_candidates
                    ],
                    "analysisWarnings": list(analysis.warnings),
                }
        raise ChatGPTQueryError(
            "CHATGPT_TASK_NOT_FOUND", "ChatGPT Task was not found", status_code=404
        )

    def messages(
        self,
        session_id: str,
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        values = list(self._latest(session_id).projection.messages)
        offset = _decode_cursor(cursor)
        page = values[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "items": [_message(item) for item in page],
            "nextCursor": (
                _encode_cursor(next_offset) if next_offset < len(values) else None
            ),
            "hasMore": next_offset < len(values),
            "total": len(values),
        }

    def graph(
        self,
        *,
        session_id: str | None = None,
        limit: int = MAX_GRAPH_NODES,
    ) -> dict[str, Any]:
        revisions = (
            (self._latest(session_id),)
            if session_id is not None
            else self._latest_revisions()
        )
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        for revision in revisions:
            session = revision.projection.session
            analysis = self._analysis(revision)
            session_node = _session_node_id(session.session_id)
            nodes.append(
                {
                    "id": session_node,
                    "type": "CHATGPT_SESSION",
                    "label": session.title,
                    "metadata": {
                        "sessionId": session.session_id,
                        "source": session.source.value,
                        "messageCount": len(revision.projection.messages),
                    },
                }
            )
            for message in revision.projection.messages:
                message_node = _message_node_id(session.session_id, message.message_id)
                nodes.append(
                    {
                        "id": message_node,
                        "type": "CHATGPT_MESSAGE",
                        "label": f"{message.role.value} #{message.sequence}",
                        "metadata": {
                            "sessionId": session.session_id,
                            "messageId": message.message_id,
                            "role": message.role.value,
                            "sequence": message.sequence,
                        },
                    }
                )
                edges.append(
                    {
                        "id": f"contains:{session_node}:{message_node}",
                        "from": session_node,
                        "to": message_node,
                        "type": "contains_message",
                        "status": "confirmed",
                    }
                )
            for task in analysis.tasks:
                nodes.append(
                    {
                        "id": task.task_id,
                        "type": "TASK",
                        "label": task.title,
                        "metadata": {
                            "sessionId": session.session_id,
                            "taskId": task.task_id,
                            "status": task.status.value,
                            "boundaryStatus": task.boundary_status.value,
                            "confidence": task.provenance.confidence,
                        },
                    }
                )
                edges.append(
                    {
                        "id": f"contains-task:{session_node}:{task.task_id}",
                        "from": session_node,
                        "to": task.task_id,
                        "type": "contains_task",
                        "status": task.boundary_status.value,
                    }
                )
            for activity in analysis.activities:
                nodes.append(
                    {
                        "id": activity.activity_id,
                        "type": "ACTIVITY",
                        "label": (
                            f"{activity.activity_type.value} #{activity.sequence}"
                        ),
                        "metadata": {
                            "sessionId": session.session_id,
                            "taskId": activity.task_id,
                            "activityId": activity.activity_id,
                            "activityType": activity.activity_type.value,
                            "sequence": activity.sequence,
                        },
                    }
                )
                edges.append(
                    {
                        "id": (
                            f"contains-activity:{activity.task_id}:"
                            f"{activity.activity_id}"
                        ),
                        "from": activity.task_id,
                        "to": activity.activity_id,
                        "type": "contains_activity",
                        "status": "confirmed",
                    }
                )
                for message_id in activity.entity_refs:
                    message_node = _message_node_id(session.session_id, message_id)
                    edges.append(
                        {
                            "id": (
                                f"derived-from:{activity.activity_id}:{message_node}"
                            ),
                            "from": activity.activity_id,
                            "to": message_node,
                            "type": "derived_from",
                            "status": "confirmed",
                        }
                    )
        truncated = len(nodes) > limit
        if truncated:
            kept_ids = {item["id"] for item in nodes[:limit]}
            nodes = nodes[:limit]
            edges = [
                item
                for item in edges
                if item["from"] in kept_ids and item["to"] in kept_ids
            ]
        return {
            "nodes": nodes,
            "edges": edges,
            "truncated": truncated,
            "limit": limit,
            "depth": 1,
        }

    def _latest(self, session_id: str) -> ChatGPTProjectionRevision:
        try:
            return self.projection_store.latest(session_id)
        except ChatGPTImportError as error:
            status_code = 404 if error.code == "CHATGPT_PROJECTION_NOT_FOUND" else 500
            raise ChatGPTQueryError(
                error.code, str(error), status_code=status_code
            ) from error

    def _latest_revisions(self) -> tuple[ChatGPTProjectionRevision, ...]:
        try:
            return self.projection_store.latest_revisions()
        except ChatGPTImportError as error:
            raise ChatGPTQueryError(error.code, str(error), status_code=500) from error

    def _analysis(self, revision: ChatGPTProjectionRevision) -> TaskAnalysis:
        projection = revision.projection
        if revision.adapter_version != "1.0.0":
            return TaskAnalysis(
                tasks=projection.tasks,
                activities=projection.activities,
                boundary_candidates=projection.boundary_candidates,
                warnings=projection.analysis_warnings,
            )
        return self.task_analyzer.analyze(
            projection.session,
            projection.messages,
        )

    @staticmethod
    def _summary(revision: ChatGPTProjectionRevision) -> dict[str, Any]:
        session = revision.projection.session
        return {
            "sessionId": session.session_id,
            "title": session.title,
            "source": session.source.value,
            "createdAt": session.created_at.isoformat(),
            "updatedAt": session.updated_at.isoformat(),
            "messageCount": len(revision.projection.messages),
            "revision": revision.revision,
            "projectedAt": revision.projected_at.isoformat(),
            "warningCount": len(revision.projection.warnings),
        }


def install_chatgpt_query_api(
    application: FastAPI, service: ChatGPTQueryService
) -> None:
    def failure(error: ChatGPTQueryError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": str(error)}},
        )

    @application.get("/api/v1/chatgpt/sessions", response_model=None)
    def sessions(
        q: str | None = Query(None, max_length=200),
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.list_sessions(query=q, cursor=cursor, limit=limit)
        except ChatGPTQueryError as error:
            return failure(error)

    @application.get(
        "/api/v1/chatgpt/sessions/{session_id}/messages", response_model=None
    )
    def messages(
        session_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.messages(session_id, cursor=cursor, limit=limit)
        except ChatGPTQueryError as error:
            return failure(error)

    @application.get("/api/v1/chatgpt/sessions/{session_id}", response_model=None)
    def detail(session_id: str) -> dict[str, Any] | JSONResponse:
        try:
            return service.detail(session_id)
        except ChatGPTQueryError as error:
            return failure(error)

    @application.get("/api/v1/chatgpt/tasks", response_model=None)
    def tasks(
        session_id: str | None = Query(None, alias="sessionId"),
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.list_tasks(
                session_id=session_id,
                cursor=cursor,
                limit=limit,
            )
        except ChatGPTQueryError as error:
            return failure(error)

    @application.get("/api/v1/chatgpt/tasks/{task_id}", response_model=None)
    def task_detail(task_id: str) -> dict[str, Any] | JSONResponse:
        try:
            return service.task_detail(task_id)
        except ChatGPTQueryError as error:
            return failure(error)

    @application.get("/api/v1/chatgpt/graph", response_model=None)
    def graph(
        session_id: str | None = Query(None, alias="sessionId"),
        limit: int = Query(MAX_GRAPH_NODES, ge=1, le=MAX_GRAPH_NODES),
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.graph(session_id=session_id, limit=limit)
        except ChatGPTQueryError as error:
            return failure(error)


def _message(value: Message) -> dict[str, Any]:
    return {
        "messageId": value.message_id,
        "sessionId": value.session_id,
        "role": value.role.value,
        "content": value.content,
        "timestamp": value.timestamp.isoformat() if value.timestamp else None,
        "sequence": value.sequence,
        "sourceMessageId": value.source_message_id,
        "provenance": _provenance(value.provenance),
    }


def _task(value: Task) -> dict[str, Any]:
    return {
        "taskId": value.task_id,
        "sessionId": value.session_id,
        "title": value.title,
        "summary": value.summary,
        "status": value.status.value,
        "boundaryStatus": value.boundary_status.value,
        "startedAt": value.started_at.isoformat() if value.started_at else None,
        "completedAt": value.completed_at.isoformat() if value.completed_at else None,
        "messageRange": {
            "startSequence": value.message_range.start_sequence,
            "endSequence": value.message_range.end_sequence,
        },
        "activityIds": list(value.activity_ids),
        "provenance": _provenance(value.provenance),
    }


def _activity(value: Activity) -> dict[str, Any]:
    return {
        "activityId": value.activity_id,
        "taskId": value.task_id,
        "activityType": value.activity_type.value,
        "sequence": value.sequence,
        "timestamp": value.timestamp.isoformat() if value.timestamp else None,
        "summary": value.summary,
        "entityRefs": list(value.entity_refs),
        "provenance": _provenance(value.provenance),
    }


def _boundary_candidate(value: TaskBoundaryCandidate) -> dict[str, Any]:
    return {
        "messageSequence": value.message_sequence,
        "confidence": value.confidence,
        "reasons": list(value.reasons),
        "provenance": _provenance(value.provenance),
    }


def _provenance(value: Provenance) -> dict[str, Any]:
    return {
        "source": value.source.value,
        "derivedBy": value.derived_by.value if value.derived_by else None,
        "confidence": value.confidence,
        "sourceRefs": list(value.source_refs),
    }


def _session_node_id(session_id: str) -> str:
    return f"chatgpt-session:{session_id}"


def _message_node_id(session_id: str, message_id: str) -> str:
    return f"chatgpt-message:{session_id}:{message_id}"


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = int(base64.urlsafe_b64decode(padded).decode())
    except (ValueError, UnicodeError) as error:
        raise ChatGPTQueryError("CHATGPT_CURSOR_INVALID", "Invalid cursor") from error
    if value < 0:
        raise ChatGPTQueryError("CHATGPT_CURSOR_INVALID", "Invalid cursor")
    return value
