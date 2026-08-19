from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoknowledge_lite.chatgpt_import import ChatGPTProjectionStore
from autoknowledge_lite.chatgpt_knowledge_adapter import ChatGPTKnowledgeAdapter
from autoknowledge_lite.chatgpt_query import (
    ChatGPTQueryService,
    install_chatgpt_query_api,
)
from autoknowledge_lite.chatgpt_session_source import ChatGPTSessionReference


def projection(session_id: str = "session-1"):
    return ChatGPTKnowledgeAdapter().project(
        {
            "id": session_id,
            "title": "Viewer shared design",
            "create_time": 1_700_000_000,
            "update_time": 1_700_000_100,
            "current_node": "message-2",
            "mapping": {
                "message-1": {
                    "id": "message-1",
                    "parent": None,
                    "message": {
                        "id": "message-1",
                        "author": {"role": "user"},
                        "create_time": 1_700_000_000,
                        "content": {"parts": ["Show this session"]},
                    },
                },
                "message-2": {
                    "id": "message-2",
                    "parent": "message-1",
                    "message": {
                        "id": "message-2",
                        "author": {"role": "assistant"},
                        "create_time": 1_700_000_100,
                        "content": {"parts": ["Session is visible"]},
                    },
                },
            },
        }
    )


def api(tmp_path: Path) -> TestClient:
    store = ChatGPTProjectionStore(
        tmp_path,
        clock=lambda: datetime(2026, 8, 19, tzinfo=UTC),
    )
    value = projection()
    store.save(
        value,
        import_id="chatgpt-test",
        session_ref=ChatGPTSessionReference(
            source_session_id="session-1",
            title="Viewer shared design",
            source_member="chatgpt-share:test",
            source_index=0,
            source_format="chatgpt_shared_link",
        ),
        source_content_hash="a" * 64,
    )
    application = FastAPI()
    install_chatgpt_query_api(
        application,
        ChatGPTQueryService(tmp_path, projection_store=store),
    )
    return TestClient(application)


def test_lists_and_searches_latest_sessions_without_raw_storage_fields(
    tmp_path: Path,
) -> None:
    response = api(tmp_path).get("/api/v1/chatgpt/sessions", params={"q": "visible"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    item = response.json()["items"][0]
    assert item["sessionId"] == "session-1"
    assert item["messageCount"] == 2
    assert "importId" not in item
    assert "sourceContentHash" not in item
    assert "sourceFile" not in item


def test_returns_session_detail_and_paginated_original_messages(tmp_path: Path) -> None:
    client = api(tmp_path)

    detail = client.get("/api/v1/chatgpt/sessions/session-1")
    first = client.get(
        "/api/v1/chatgpt/sessions/session-1/messages", params={"limit": 1}
    )
    second = client.get(
        "/api/v1/chatgpt/sessions/session-1/messages",
        params={"limit": 1, "cursor": first.json()["nextCursor"]},
    )

    assert detail.status_code == 200
    assert detail.json()["session"]["provenance"]["source"] == "original"
    assert len(detail.json()["session"]["taskIds"]) == 1
    assert first.json()["items"][0]["content"] == "Show this session"
    assert first.json()["items"][0]["provenance"]["source"] == "original"
    assert second.json()["items"][0]["content"] == "Session is visible"


def test_lists_derived_tasks_and_returns_activity_flow(tmp_path: Path) -> None:
    client = api(tmp_path)

    listing = client.get("/api/v1/chatgpt/tasks", params={"sessionId": "session-1"})
    task_id = listing.json()["items"][0]["taskId"]
    detail = client.get(f"/api/v1/chatgpt/tasks/{task_id}")

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["provenance"] == {
        "source": "derived",
        "derivedBy": "rule",
        "confidence": 1.0,
        "sourceRefs": [
            "session:session-1",
            "message:message-1",
            "message:message-2",
        ],
    }
    assert detail.status_code == 200
    assert [item["activityType"] for item in detail.json()["activities"]] == [
        "request",
        "response",
    ]
    assert all(
        item["provenance"]["source"] == "derived"
        for item in detail.json()["activities"]
    )


def test_reanalyzes_legacy_projection_without_rewriting_revision(
    tmp_path: Path,
) -> None:
    store = ChatGPTProjectionStore(
        tmp_path,
        clock=lambda: datetime(2026, 8, 19, tzinfo=UTC),
    )
    write = store.save(
        projection(),
        import_id="legacy-test",
        session_ref=ChatGPTSessionReference(
            source_session_id="session-1",
            title="Viewer shared design",
            source_member="conversations.json",
            source_index=0,
            source_format="chatgpt_data_export",
        ),
        source_content_hash="b" * 64,
    )
    legacy = write.record.model_copy(
        update={
            "adapter_version": "1.0.0",
            "projection": write.record.projection.model_copy(
                update={"tasks": (), "activities": ()}
            ),
        }
    )
    original_revision = write.revision_path.read_bytes()

    class LegacyStore:
        def latest(self, _session_id: str):
            return legacy

        def latest_revisions(self):
            return (legacy,)

    service = ChatGPTQueryService(tmp_path, projection_store=LegacyStore())

    assert service.list_tasks(session_id="session-1")["total"] == 1
    assert write.revision_path.read_bytes() == original_revision


def test_returns_session_message_knowledge_graph(tmp_path: Path) -> None:
    response = api(tmp_path).get(
        "/api/v1/chatgpt/graph", params={"sessionId": "session-1"}
    )

    assert response.status_code == 200
    graph = response.json()
    assert {item["type"] for item in graph["nodes"]} == {
        "CHATGPT_SESSION",
        "CHATGPT_MESSAGE",
    }
    assert len(graph["edges"]) == 2
    assert {item["type"] for item in graph["edges"]} == {"contains_message"}
    assert all("content" not in item["metadata"] for item in graph["nodes"])


def test_missing_session_and_invalid_cursor_are_safe_errors(tmp_path: Path) -> None:
    client = api(tmp_path)

    missing = client.get("/api/v1/chatgpt/sessions/missing")
    invalid = client.get("/api/v1/chatgpt/sessions", params={"cursor": "%%%"})
    missing_task = client.get("/api/v1/chatgpt/tasks/missing")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CHATGPT_PROJECTION_NOT_FOUND"
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "CHATGPT_CURSOR_INVALID"
    assert missing_task.status_code == 404
    assert missing_task.json()["error"]["code"] == "CHATGPT_TASK_NOT_FOUND"
