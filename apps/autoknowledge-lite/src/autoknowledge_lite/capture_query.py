"""Read-only Capture Viewer queries built on the persisted Capture projection."""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from autoknowledge_lite.capture_relations import (
    CaptureRelationRepository,
    RelationStatus,
)

DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100
DEFAULT_GRAPH_DEPTH = 2
MAX_GRAPH_DEPTH = 4
MAX_GRAPH_NODES = 300
MAX_TEXT_PREVIEW = 20_000
MAX_DIFF_PREVIEW_BYTES = 500 * 1024
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")


class CaptureQueryError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class CaptureMetadataUpdate(BaseModel):
    """Editable Capture metadata; collected evidence is intentionally absent."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str | None = Field(default=None, max_length=200)
    tags: list[str] | None = None
    project_id: str | None = Field(default=None, alias="projectId", max_length=200)
    parent_document: str | None = Field(
        default=None, alias="parentDocument", max_length=2_000
    )
    user_note: str | None = Field(default=None, alias="userNote", max_length=20_000)


class CaptureQueryService:
    """Query and graph facade over the relation repository's safe projection."""

    def __init__(self, repository: CaptureRelationRepository) -> None:
        self.repository = repository
        self.notes_path = repository.root / "capture-viewer-metadata-v1.json"

    def list_captures(
        self,
        *,
        query: str | None = None,
        source_type: str | None = None,
        capture_type: str | None = None,
        capture_device: str | None = None,
        project_id: str | None = None,
        status: str | None = None,
        test_status: str | None = None,
        relation_status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        sort: str = "newest",
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
        include_large_content: bool = False,
    ) -> dict[str, Any]:
        records = [self._merged(item) for item in self.repository.captures()]
        filtered: list[tuple[dict[str, Any], dict[str, str] | None]] = []
        for item in records:
            if source_type and item.get("sourceType") != source_type:
                continue
            if capture_type and item.get("captureType") != capture_type:
                continue
            if capture_device and item.get("captureDevice") != capture_device:
                continue
            if project_id:
                if project_id == "__none__":
                    if item.get("projectId"):
                        continue
                elif item.get("projectId") != project_id:
                    continue
            if status and self._capture_status(item) != status:
                continue
            if test_status and self._test_status(item) != test_status:
                continue
            if (
                relation_status
                and self._relation_status(item["captureId"]) != relation_status
            ):
                continue
            captured = _parse_time(item.get("capturedAt"))
            if from_date and (not captured or captured < _aware(from_date)):
                continue
            if to_date and (not captured or captured > _aware(to_date)):
                continue
            match = self._search_match(item, query, include_large_content)
            if query and not match:
                continue
            filtered.append((item, match))

        reverse = sort not in {"oldest", "title"}

        def key(pair: tuple[dict[str, Any], dict[str, str] | None]) -> Any:
            if sort == "title":
                return str(pair[0].get("title") or "").casefold()
            if sort == "changed_files":
                return len(self._session(pair[0]).get("changedFiles", []))
            if sort == "test_failures":
                return (
                    self._test_status(pair[0]) == "failed",
                    pair[0].get("capturedAt", ""),
                )
            if sort == "relevance" and query:
                return self._match_rank(pair[1]), pair[0].get("capturedAt", "")
            return pair[0].get("capturedAt", "")

        filtered.sort(key=key, reverse=reverse)
        offset = _decode_cursor(cursor)
        page = filtered[offset : offset + limit]
        next_offset = offset + len(page)
        return {
            "items": [self._summary(item, match) for item, match in page],
            "nextCursor": (
                _encode_cursor(next_offset) if next_offset < len(filtered) else None
            ),
            "hasMore": next_offset < len(filtered),
            "total": len(filtered),
        }

    def detail(self, capture_id: str) -> dict[str, Any]:
        item = self._required(capture_id)
        session = self._session(item)
        relations = self._relations(capture_id)
        base = {
            "capture": self._summary(item),
            "metadata": {
                "captureId": capture_id,
                "documentId": item.get("documentId"),
                "schemaVersion": "1.0",
                "captureMethod": item.get("captureMethod"),
                "contentHash": item.get("contentHash"),
                "revision": item.get("revision", 1),
                "parentDocument": item.get("parentDocument"),
                "sourceSessionId": session.get("sourceSessionId"),
                "adapterName": (session.get("adapter") or {}).get("name"),
                "adapterVersion": (session.get("adapter") or {}).get("version"),
                "documentPath": _safe_path(item.get("documentPath")),
            },
            "relations": relations,
            "relationCandidates": [r for r in relations if r["status"] == "suggested"],
            "userNote": item.get("userNote"),
            "tags": item.get("tags", []),
        }
        if item.get("captureType") == "clipboard_item":
            base.update(
                {
                    "content": item.get("normalizedContent", ""),
                    "relatedSessions": [
                        self._summary(self._required(r["toCaptureId"]))
                        | {"relation": r}
                        for r in relations
                        if r["direction"] == "out"
                    ],
                }
            )
            return base
        base.update(
            {
                "summary": {
                    "request": session.get("request")
                    or session.get("firstCodexUserMessage"),
                    "summary": session.get("summary"),
                    "repository": self._repository(session.get("repository")),
                    "startedAt": session.get("startedAt") or item.get("capturedAt"),
                    "endedAt": session.get("endedAt"),
                    "closureReason": session.get("closureReason"),
                    "clientType": session.get("clientType") or item.get("clientType"),
                },
                "messagesSummary": {"count": len(session.get("messages", []))},
                "commandsSummary": {"count": len(session.get("commands", []))},
                "changedFilesSummary": {"count": len(session.get("changedFiles", []))},
                "testsSummary": {
                    "count": len(session.get("tests", [])),
                    "status": self._test_status(item),
                },
                "attachmentsSummary": {"count": len(session.get("attachments", []))},
                "tasks": self._tasks(item),
            }
        )
        return base

    def child_items(
        self,
        capture_id: str,
        collection: Literal[
            "messages", "commands", "changedFiles", "tests", "attachments"
        ],
        *,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> dict[str, Any]:
        session = self._session(self._required_session(capture_id))
        values = session.get(collection, [])
        if not isinstance(values, list):
            values = []
        offset = _decode_cursor(cursor)
        page = values[offset : offset + limit]
        if collection == "commands":
            page = [self._command(item) for item in page]
        elif collection == "changedFiles":
            page = [self._changed_file(item) for item in page]
        elif collection == "attachments":
            page = [self._attachment(item, include_content=False) for item in page]
        tasks = self._tasks(self._required_session(capture_id))
        if tasks:
            task_id = tasks[0]["taskId"]
            page = [dict(item) | {"taskId": task_id} for item in page]
        next_offset = offset + len(page)
        return {
            "items": page,
            "nextCursor": (
                _encode_cursor(next_offset) if next_offset < len(values) else None
            ),
            "hasMore": next_offset < len(values),
            "total": len(values),
        }

    def diffs(self, capture_id: str) -> dict[str, Any]:
        session = self._session(self._required_session(capture_id))
        values = []
        for item in session.get("attachments", []):
            kind = str(item.get("type") or "").casefold()
            name = str(item.get("name") or "")
            if kind not in {"patch", "diff"} and not name.casefold().endswith(
                (".patch", ".diff")
            ):
                continue
            values.append(self._attachment(item, include_content=True))
        return {
            "items": values,
            "total": len(values),
            "previewLimitBytes": MAX_DIFF_PREVIEW_BYTES,
        }

    def update_metadata(
        self, capture_id: str, update: CaptureMetadataUpdate
    ) -> dict[str, Any]:
        self._required(capture_id)
        metadata = self._viewer_metadata()
        current = dict(metadata.get(capture_id, {}))
        changes = update.model_dump(exclude_unset=True, by_alias=True)
        changes["updatedAt"] = datetime.now(UTC).isoformat()
        current.update(changes)
        metadata[capture_id] = current
        self._write_metadata(metadata)
        return self.detail(capture_id)

    def file_history(self, path: str) -> dict[str, Any]:
        normalized = _normalize_repo_path(path)
        sessions = []
        for item in self.repository.captures():
            if item.get("captureType") != "development_session":
                continue
            for changed in self._session(item).get("changedFiles", []):
                if _normalize_repo_path(str(changed.get("path") or "")) == normalized:
                    sessions.append(
                        {
                            "captureId": item["captureId"],
                            "title": item.get("title"),
                            "changedAt": item.get("capturedAt"),
                            "changeType": changed.get("changeType", "unknown"),
                        }
                    )
        sessions.sort(key=lambda value: value.get("changedAt") or "", reverse=True)
        return {"path": _safe_path(normalized), "sessions": sessions}

    def document_backlinks(self, document_id: str) -> dict[str, Any]:
        """Return typed Capture backlinks without conflating excerpt relations."""

        items = []
        for record in self.repository.captures():
            item = self._merged(record)
            relation_type = None
            if item.get("parentDocument") == document_id:
                relation_type = "parent_of"
            elif item.get("documentId") == document_id:
                relation_type = "capture_document"
            if relation_type:
                items.append(self._summary(item) | {"relationType": relation_type})
        items.sort(key=lambda item: item.get("capturedAt") or "", reverse=True)
        return {"documentId": document_id, "items": items, "total": len(items)}

    def task_detail(self, task_id: str) -> dict[str, Any]:
        for record in self.repository.captures():
            item = self._merged(record)
            for task in self._tasks(item):
                if task["taskId"] == task_id:
                    return {
                        "task": task,
                        "capture": self._summary(item),
                        "navigation": {
                            "overview": f"/api/v1/captures/{item['captureId']}",
                            "messages": f"/api/v1/captures/{item['captureId']}/messages",
                            "changedFiles": f"/api/v1/captures/{item['captureId']}/changed-files",
                            "commands": f"/api/v1/captures/{item['captureId']}/commands",
                            "tests": f"/api/v1/captures/{item['captureId']}/tests",
                            "graph": f"/api/v1/graph/neighborhood/{task_id}",
                        },
                    }
        raise CaptureQueryError("TASK_NOT_FOUND", task_id, status_code=404)

    def graph(
        self,
        *,
        center_id: str | None = None,
        project_id: str | None = None,
        node_types: set[str] | None = None,
        relation_types: set[str] | None = None,
        test_status: str | None = None,
        source_type: str | None = None,
        include_candidates: bool = False,
        depth: int = DEFAULT_GRAPH_DEPTH,
        limit: int = MAX_GRAPH_NODES,
    ) -> dict[str, Any]:
        captures = {
            item["captureId"]: self._merged(item) for item in self.repository.captures()
        }
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        def add_node(
            node_id: str,
            node_type: str,
            label: str,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if node_types and node_type not in node_types:
                return
            nodes[node_id] = {
                "id": node_id,
                "type": node_type,
                "label": label,
                "metadata": metadata or {},
            }

        def add_edge(
            edge_id: str, source: str, target: str, kind: str, status: str = "confirmed"
        ) -> None:
            if relation_types and kind not in relation_types:
                return
            edges.append(
                {
                    "id": edge_id,
                    "from": source,
                    "to": target,
                    "type": kind,
                    "status": status,
                }
            )

        for capture_id, item in captures.items():
            if project_id and item.get("projectId") != project_id:
                continue
            if source_type and item.get("sourceType") != source_type:
                continue
            if test_status and self._test_status(item) != test_status:
                continue
            node_type = (
                "DEVELOPMENT_SESSION"
                if item.get("captureType") == "development_session"
                else "CLIPBOARD_CAPTURE"
            )
            add_node(
                capture_id,
                node_type,
                self._title(item),
                {
                    "captureType": item.get("captureType"),
                    "sourceType": item.get("sourceType"),
                    "testStatus": self._test_status(item),
                },
            )
            if item.get("documentId"):
                document_id = str(item["documentId"])
                add_node(
                    document_id,
                    "DOCUMENT",
                    self._title(item),
                    {"path": _safe_path(item.get("documentPath"))},
                )
                add_edge(
                    f"document-{capture_id}", capture_id, document_id, "references"
                )
            project = item.get("projectId")
            if project:
                project_node = f"project:{project}"
                add_node(project_node, "PROJECT", str(project))
                add_edge(
                    f"project-{capture_id}",
                    capture_id,
                    project_node,
                    "belongs_to_project",
                )
            parent = item.get("parentDocument")
            if parent:
                add_node(str(parent), "DOCUMENT", str(parent))
                add_edge(f"parent-{capture_id}", str(parent), capture_id, "parent_of")
            if item.get("captureType") != "development_session":
                continue
            session = self._session(item)
            tasks = self._tasks(item)
            task_id = tasks[0]["taskId"] if tasks else None
            if task_id:
                task = tasks[0]
                add_node(
                    task_id,
                    "TASK",
                    task["title"],
                    {
                        "status": task["status"],
                        "boundaryStatus": task["boundaryStatus"],
                        "confidence": task["confidence"],
                        "captureId": capture_id,
                    },
                )
                add_edge(
                    f"task-{capture_id}",
                    capture_id,
                    task_id,
                    "contains_task",
                )
            for index, changed in enumerate(session.get("changedFiles", []), 1):
                file_id = (
                    f"file:{_normalize_repo_path(str(changed.get('path') or index))}"
                )
                add_node(
                    file_id,
                    "FILE",
                    _safe_path(changed.get("path")),
                    {"changeType": changed.get("changeType")},
                )
                add_edge(
                    f"changed-{capture_id}-{index}", capture_id, file_id, "changed_file"
                )
                if task_id:
                    add_edge(
                        f"task-changed-{capture_id}-{index}",
                        task_id,
                        file_id,
                        "modifies",
                    )
            for index, command in enumerate(session.get("commands", []), 1):
                command_id = str(
                    command.get("commandId") or f"command:{capture_id}:{index}"
                )
                add_node(
                    command_id,
                    "COMMAND",
                    str(command.get("command") or "명령"),
                    {"exitCode": command.get("exitCode")},
                )
                add_edge(
                    f"command-{capture_id}-{index}",
                    capture_id,
                    command_id,
                    "executed_command",
                )
                if task_id:
                    add_edge(
                        f"task-command-{capture_id}-{index}",
                        task_id,
                        command_id,
                        "executes",
                    )
            for index, test in enumerate(session.get("tests", []), 1):
                test_id = str(test.get("testId") or f"test:{capture_id}:{index}")
                add_node(
                    test_id,
                    "TEST_RESULT",
                    str(test.get("framework") or test.get("tool") or "테스트"),
                    {"status": str(test.get("status") or "UNKNOWN").lower()},
                )
                add_edge(f"test-{capture_id}-{index}", capture_id, test_id, "tested_by")
                if task_id:
                    add_edge(
                        f"task-test-{capture_id}-{index}", task_id, test_id, "runs"
                    )
        for relation in self.repository.relations():
            if relation.status != RelationStatus.CONFIRMED and not include_candidates:
                continue
            add_edge(
                relation.relation_id,
                relation.from_capture_id,
                relation.to_capture_id,
                relation.relation_type,
                relation.status.value,
            )

        edges = [
            edge for edge in edges if edge["from"] in nodes and edge["to"] in nodes
        ]

        if center_id:
            if center_id not in nodes:
                raise CaptureQueryError(
                    "GRAPH_NODE_NOT_FOUND", center_id, status_code=404
                )
            allowed = _neighborhood(center_id, edges, depth)
            nodes = {key: value for key, value in nodes.items() if key in allowed}
            edges = [
                edge for edge in edges if edge["from"] in nodes and edge["to"] in nodes
            ]
        truncated = len(nodes) > limit
        if truncated:
            keep = set(list(nodes)[:limit])
            if center_id:
                keep.add(center_id)
            nodes = {key: value for key, value in nodes.items() if key in keep}
            edges = [
                edge for edge in edges if edge["from"] in nodes and edge["to"] in nodes
            ]
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "truncated": truncated,
            "limit": limit,
            "depth": depth,
        }

    def _required(self, capture_id: str) -> dict[str, Any]:
        item = self.repository.capture(capture_id)
        if not item:
            raise CaptureQueryError("CAPTURE_NOT_FOUND", capture_id, status_code=404)
        return self._merged(item)

    def _required_session(self, capture_id: str) -> dict[str, Any]:
        item = self._required(capture_id)
        if item.get("captureType") != "development_session":
            raise CaptureQueryError(
                "CAPTURE_DETAIL_LOAD_FAILED", "development_session required"
            )
        return item

    @staticmethod
    def _session(item: dict[str, Any]) -> dict[str, Any]:
        value = item.get("session")
        if isinstance(value, dict):
            return value
        return {"messages": item.get("messages", [])}

    def _merged(self, item: dict[str, Any]) -> dict[str, Any]:
        return dict(item) | dict(self._viewer_metadata().get(item["captureId"], {}))

    def _summary(
        self, item: dict[str, Any], match: dict[str, str] | None = None
    ) -> dict[str, Any]:
        session = self._session(item)
        return {
            "captureId": item["captureId"],
            "documentId": item.get("documentId"),
            "title": self._title(item),
            "sourceType": item.get("sourceType"),
            "captureType": item.get("captureType"),
            "captureDevice": item.get("captureDevice"),
            "projectId": item.get("projectId"),
            "capturedAt": item.get("capturedAt"),
            "status": self._capture_status(item),
            "testStatus": self._test_status(item),
            "relationStatus": self._relation_status(item["captureId"]),
            "changedFilesCount": len(session.get("changedFiles", [])),
            "commandsCount": len(session.get("commands", [])),
            "relationCount": len(self._relations(item["captureId"])),
            "match": match,
        }

    def _tasks(self, item: dict[str, Any]) -> list[dict[str, Any]]:
        if item.get("captureType") != "development_session":
            return []
        session = self._session(item)
        request = str(
            session.get("request") or session.get("firstCodexUserMessage") or ""
        ).strip()
        messages = session.get("messages", [])
        commands = session.get("commands", [])
        changed_files = session.get("changedFiles", [])
        tests = session.get("tests", [])
        if not any((request, messages, commands, changed_files, tests)):
            return []
        capture_id = str(item["captureId"])
        title = request.splitlines()[0][:120] if request else self._title(item)
        sequences = [
            value
            for message in messages
            if isinstance(message, dict)
            for value in [message.get("sequence")]
            if isinstance(value, int) and not isinstance(value, bool) and value > 0
        ]
        return [
            {
                "taskId": f"task:{capture_id}:session",
                "sessionId": capture_id,
                "captureId": capture_id,
                "title": title,
                "summary": session.get("summary"),
                "status": "completed" if session.get("endedAt") else "in_progress",
                "boundaryStatus": "suggested",
                "confidence": 0.5,
                "messageRange": (
                    {"startSequence": min(sequences), "endSequence": max(sequences)}
                    if sequences
                    else None
                ),
                "counts": {
                    "messages": len(messages),
                    "changedFiles": len(changed_files),
                    "commands": len(commands),
                    "tests": len(tests),
                },
                "provenance": {
                    "source": "derived",
                    "derivedBy": "rule",
                    "sourceRefs": [f"capture:{capture_id}"],
                },
            }
        ]

    def _relations(self, capture_id: str) -> list[dict[str, Any]]:
        values = []
        for relation in self.repository.relations():
            if (
                relation.from_capture_id != capture_id
                and relation.to_capture_id != capture_id
            ):
                continue
            target_id = (
                relation.to_capture_id
                if relation.from_capture_id == capture_id
                else relation.from_capture_id
            )
            target = self.repository.capture(target_id) or {}
            values.append(
                relation.model_dump(mode="json", by_alias=True)
                | {
                    "direction": (
                        "out" if relation.from_capture_id == capture_id else "in"
                    ),
                    "targetTitle": target.get("title"),
                }
            )
        return values

    def _relation_status(self, capture_id: str) -> str:
        statuses = {
            r.status
            for r in self.repository.relations()
            if capture_id in {r.from_capture_id, r.to_capture_id}
        }
        if RelationStatus.STALE in statuses:
            return "stale"
        if RelationStatus.CONFIRMED in statuses:
            return "linked"
        if RelationStatus.SUGGESTED in statuses:
            return "suggested"
        return "unlinked"

    def _capture_status(self, item: dict[str, Any]) -> str:
        explicit = item.get("status") or item.get("metadata", {}).get("status")
        if explicit:
            return str(explicit).casefold()
        session = self._session(item)
        return (
            "completed"
            if item.get("captureType") == "clipboard_item" or session.get("endedAt")
            else "in_progress"
        )

    def _test_status(self, item: dict[str, Any]) -> str:
        tests = self._session(item).get("tests", [])
        if not tests:
            return "none"
        statuses = {str(test.get("status") or "UNKNOWN").upper() for test in tests}
        if statuses & {"FAILED", "TIMED_OUT", "CANCELLED"}:
            return "failed"
        if "PARTIAL" in statuses or ("PASSED" in statuses and len(statuses) > 1):
            return "partial"
        if statuses <= {"PASSED", "SKIPPED"} and "PASSED" in statuses:
            return "passed"
        return "unknown"

    def _search_match(
        self, item: dict[str, Any], query: str | None, include_large: bool
    ) -> dict[str, str] | None:
        if not query:
            return None
        needle = query.casefold().strip()
        session = self._session(item)
        fields: list[tuple[str, str]] = [
            ("제목", self._title(item)),
            ("본문", str(item.get("normalizedContent") or "")),
            ("프로젝트", str(item.get("projectId") or "")),
            ("브랜치", str((session.get("repository") or {}).get("branch") or "")),
            ("상위 주제", str(item.get("parentDocument") or "")),
            ("태그", " ".join(item.get("tags", []))),
        ]
        fields.extend(
            (
                "대화",
                str(message.get("content") or message.get("normalizedContent") or ""),
            )
            for message in session.get("messages", [])
        )
        fields.extend(
            ("명령", str(command.get("command") or ""))
            for command in session.get("commands", [])
        )
        fields.extend(
            ("파일", str(changed.get("path") or ""))
            for changed in session.get("changedFiles", [])
        )
        fields.extend(
            ("테스트", str(test.get("framework") or test.get("tool") or ""))
            for test in session.get("tests", [])
        )
        if include_large:
            fields.extend(
                (
                    "명령 출력",
                    f"{command.get('stdout', '')} {command.get('stderr', '')}",
                )
                for command in session.get("commands", [])
            )
            fields.extend(
                ("Diff", str(attachment.get("content") or ""))
                for attachment in session.get("attachments", [])
            )
        for label, value in fields:
            index = value.casefold().find(needle)
            if index >= 0:
                start = max(0, index - 60)
                return {
                    "field": label,
                    "snippet": value[start : index + len(query) + 100],
                }
        return None

    @staticmethod
    def _match_rank(match: dict[str, str] | None) -> int:
        return {"제목": 5, "프로젝트": 4, "본문": 3, "대화": 2}.get(
            (match or {}).get("field", ""), 1
        )

    @staticmethod
    def _title(item: dict[str, Any]) -> str:
        title = str(item.get("title") or "").strip()
        if title:
            return title
        return (
            "Codex 전체 작업"
            if item.get("captureType") == "development_session"
            else "저장된 클립보드"
        )

    @staticmethod
    def _repository(value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: (
                _safe_path(item)
                if "path" in key.casefold() or "root" in key.casefold()
                else item
            )
            for key, item in value.items()
        }

    @staticmethod
    def _command(item: dict[str, Any]) -> dict[str, Any]:
        result = dict(item)
        for key in ("workingDirectory", "cwd"):
            if key in result:
                result[key] = _safe_path(result[key])
        for key in ("stdout", "stderr"):
            value = str(result.get(key) or "")
            result[f"{key}Truncated"] = len(value) > MAX_TEXT_PREVIEW
            result[f"{key}Size"] = len(value.encode("utf-8"))
            result[key] = _head_tail(value, MAX_TEXT_PREVIEW)
        return result

    @staticmethod
    def _changed_file(item: dict[str, Any]) -> dict[str, Any]:
        return dict(item) | {"path": _safe_path(item.get("path"))}

    @staticmethod
    def _attachment(item: dict[str, Any], *, include_content: bool) -> dict[str, Any]:
        content = str(item.get("content") or "")
        result = {key: value for key, value in item.items() if key != "content"}
        result["name"] = Path(str(result.get("name") or "attachment")).name
        result["size"] = len(content.encode("utf-8"))
        result["truncated"] = result["size"] > MAX_DIFF_PREVIEW_BYTES
        if include_content:
            result["content"] = _head_tail_bytes(content, MAX_DIFF_PREVIEW_BYTES)
        return result

    def _viewer_metadata(self) -> dict[str, dict[str, Any]]:
        if not self.notes_path.exists():
            return {}
        try:
            value = json.loads(self.notes_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_metadata(self, value: dict[str, dict[str, Any]]) -> None:
        self.repository._write(self.notes_path, value)


def install_capture_query_api(
    application: FastAPI, service: CaptureQueryService
) -> None:
    def failure(error: CaptureQueryError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": str(error)}},
        )

    @application.get("/api/v1/captures", response_model=None)
    def list_captures(
        q: str | None = Query(None, max_length=200),
        source_type: str | None = Query(None, alias="sourceType"),
        capture_type: str | None = Query(None, alias="captureType"),
        capture_device: str | None = Query(None, alias="captureDevice"),
        project_id: str | None = Query(None, alias="projectId"),
        capture_status: str | None = Query(None, alias="status"),
        test_status: str | None = Query(None, alias="testStatus"),
        relation_status: str | None = Query(None, alias="relationStatus"),
        from_date: datetime | None = Query(None, alias="from"),
        to_date: datetime | None = Query(None, alias="to"),
        sort: str = Query("newest"),
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
        include_large_content: bool = Query(False, alias="includeLargeContent"),
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.list_captures(
                query=q,
                source_type=source_type,
                capture_type=capture_type,
                capture_device=capture_device,
                project_id=project_id,
                status=capture_status,
                test_status=test_status,
                relation_status=relation_status,
                from_date=from_date,
                to_date=to_date,
                sort=sort,
                cursor=cursor,
                limit=limit,
                include_large_content=include_large_content,
            )
        except CaptureQueryError as error:
            return failure(error)

    @application.get("/api/v1/captures/{capture_id}", response_model=None)
    def capture_detail(capture_id: str) -> dict[str, Any] | JSONResponse:
        try:
            return service.detail(capture_id)
        except CaptureQueryError as error:
            return failure(error)

    @application.patch("/api/v1/captures/{capture_id}", response_model=None)
    def update_capture(
        capture_id: str, payload: CaptureMetadataUpdate
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.update_metadata(capture_id, payload)
        except CaptureQueryError as error:
            return failure(error)

    def child_route(
        capture_id: str, key: str, cursor: str | None, limit: int
    ) -> dict[str, Any] | JSONResponse:
        try:
            return service.child_items(capture_id, key, cursor=cursor, limit=limit)  # type: ignore[arg-type]
        except CaptureQueryError as error:
            return failure(error)

    @application.get("/api/v1/captures/{capture_id}/messages", response_model=None)
    def messages(
        capture_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        return child_route(capture_id, "messages", cursor, limit)

    @application.get("/api/v1/captures/{capture_id}/commands", response_model=None)
    def commands(
        capture_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        return child_route(capture_id, "commands", cursor, limit)

    @application.get("/api/v1/captures/{capture_id}/changed-files", response_model=None)
    def changed_files(
        capture_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        return child_route(capture_id, "changedFiles", cursor, limit)

    @application.get("/api/v1/captures/{capture_id}/tests", response_model=None)
    def tests(
        capture_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        return child_route(capture_id, "tests", cursor, limit)

    @application.get("/api/v1/captures/{capture_id}/attachments", response_model=None)
    def attachments(
        capture_id: str,
        cursor: str | None = None,
        limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    ):
        return child_route(capture_id, "attachments", cursor, limit)

    @application.get("/api/v1/captures/{capture_id}/diffs", response_model=None)
    def diffs(capture_id: str):
        try:
            return service.diffs(capture_id)
        except CaptureQueryError as error:
            return failure(error)

    @application.get("/api/v1/files/history", response_model=None)
    def file_history(path: str = Query(..., min_length=1, max_length=2_000)):
        return service.file_history(path)

    @application.get(
        "/api/v1/documents/{document_id:path}/capture-backlinks",
        response_model=None,
    )
    def document_backlinks(document_id: str):
        return service.document_backlinks(document_id)

    @application.get("/api/v1/tasks/{task_id}", response_model=None)
    def task_detail(task_id: str):
        try:
            return service.task_detail(task_id)
        except CaptureQueryError as error:
            return failure(error)

    @application.get("/api/v1/graph", response_model=None)
    def graph(
        project_id: str | None = Query(None, alias="projectId"),
        node_types: str | None = Query(None, alias="nodeTypes"),
        relation_types: str | None = Query(None, alias="relationTypes"),
        test_status: str | None = Query(None, alias="testStatus"),
        source_type: str | None = Query(None, alias="sourceType"),
        include_candidates: bool = Query(False, alias="includeCandidates"),
        depth: int = Query(DEFAULT_GRAPH_DEPTH, ge=1, le=MAX_GRAPH_DEPTH),
        limit: int = Query(MAX_GRAPH_NODES, ge=1, le=MAX_GRAPH_NODES),
    ):
        return service.graph(
            project_id=project_id,
            node_types=_csv(node_types),
            relation_types=_csv(relation_types),
            test_status=test_status,
            source_type=source_type,
            include_candidates=include_candidates,
            depth=depth,
            limit=limit,
        )

    @application.get("/api/v1/graph/neighborhood/{entity_id}", response_model=None)
    def neighborhood(
        entity_id: str,
        include_candidates: bool = Query(False, alias="includeCandidates"),
        depth: int = Query(DEFAULT_GRAPH_DEPTH, ge=1, le=MAX_GRAPH_DEPTH),
        limit: int = Query(MAX_GRAPH_NODES, ge=1, le=MAX_GRAPH_NODES),
    ):
        try:
            return service.graph(
                center_id=entity_id,
                include_candidates=include_candidates,
                depth=depth,
                limit=limit,
            )
        except CaptureQueryError as error:
            return failure(error)


def _csv(value: str | None) -> set[str] | None:
    return (
        {item.strip() for item in value.split(",") if item.strip()} if value else None
    )


def _parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return _aware(parsed)
    except (TypeError, ValueError):
        return None


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _encode_cursor(offset: int) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps({"offset": offset}).encode())
        .decode()
        .rstrip("=")
    )


def _decode_cursor(value: str | None) -> int:
    if not value:
        return 0
    try:
        padded = value + "=" * (-len(value) % 4)
        offset = int(json.loads(base64.urlsafe_b64decode(padded))["offset"])
        if offset < 0:
            raise ValueError
        return offset
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        raise CaptureQueryError(
            "INVALID_CURSOR", "페이지 커서가 유효하지 않습니다."
        ) from error


def _safe_path(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if _WINDOWS_ABSOLUTE.match(text) or text.startswith("/"):
        return f"%REPO_ROOT%/{PurePosixPath(text).name}"
    return text


def _normalize_repo_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("%REPO_ROOT%/").lstrip("./")


def _head_tail(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    half = limit // 2
    return value[:half] + "\n… 출력 일부 생략 …\n" + value[-half:]


def _head_tail_bytes(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    half = limit // 2
    return (
        encoded[:half].decode("utf-8", "ignore")
        + "\n… Diff 일부 생략 …\n"
        + encoded[-half:].decode("utf-8", "ignore")
    )


def _neighborhood(center: str, edges: list[dict[str, Any]], depth: int) -> set[str]:
    visited = {center}
    frontier = {center}
    for _ in range(depth):
        next_frontier = set()
        for edge in edges:
            if edge["from"] in frontier:
                next_frontier.add(edge["to"])
            if edge["to"] in frontier:
                next_frontier.add(edge["from"])
        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier
    return visited
