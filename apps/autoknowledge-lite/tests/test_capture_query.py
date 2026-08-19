from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.capture_api import normalize_capture_text
from autoknowledge_lite.chatgpt_import import ChatGPTProjectionStore
from autoknowledge_lite.chatgpt_knowledge_adapter import ChatGPTKnowledgeAdapter
from autoknowledge_lite.chatgpt_session_source import ChatGPTSessionReference
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


class NullIndexer:
    def index_file(self, source: str, relative_path: str):
        return {"documentId": f"doc::{relative_path}"}

    def search_documents(self, source: str, query: str, *, limit: int = 20):
        return ()

    def link_child(self, source: str, parent_document_id: str, target_document_id: str):
        return {"fileSaved": True}


def digest(value: str) -> str:
    return hashlib.sha256(normalize_capture_text(value).encode()).hexdigest()


def api(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "data"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            mde_client=NullIndexer(),
        )
    )


def save_chatgpt_projection(tmp_path: Path) -> None:
    projection = ChatGPTKnowledgeAdapter().project(
        {
            "id": "chatgpt-graph-session",
            "title": "Graph integration",
            "create_time": 1_700_000_000,
            "update_time": 1_700_000_100,
            "messages": [
                {
                    "id": "chatgpt-user",
                    "role": "user",
                    "content": "Knowledge Graph에 연결해줘",
                },
                {
                    "id": "chatgpt-assistant",
                    "role": "assistant",
                    "content": "그래프 연결을 완료했습니다.",
                },
            ],
        }
    )
    ChatGPTProjectionStore(
        tmp_path / "data",
        clock=lambda: datetime(2026, 8, 19, tzinfo=UTC),
    ).save(
        projection,
        import_id="graph-integration",
        session_ref=ChatGPTSessionReference(
            source_session_id="chatgpt-graph-session",
            title="Graph integration",
            source_member="conversations.json",
            source_index=0,
            source_format="chatgpt_data_export",
        ),
        source_content_hash="c" * 64,
    )


def envelope(capture_id: str, *, failed: bool = False) -> dict[str, object]:
    payload = {
        "captureSessionId": capture_id,
        "sourceSessionId": f"source-{capture_id}",
        "clientType": "codex_app_server",
        "title": f"Viewer integration {capture_id}",
        "request": "Capture Viewer를 구현해.",
        "summary": "목록과 그래프를 연결함",
        "startedAt": "2026-08-03T12:00:00+09:00",
        "endedAt": "2026-08-03T12:10:00+09:00",
        "repository": {
            "name": "AutoKnowledge-Lite",
            "rootAlias": "%REPO_ROOT%",
            "branch": "feature/capture-viewer",
            "worktreePathAlias": "%REPO_ROOT%",
        },
        "messages": [
            {
                "messageId": "msg_1",
                "role": "assistant",
                "messageType": "text",
                "content": "uv run pytest 명령으로 Viewer 테스트를 확인했습니다.",
                "createdAt": "2026-08-03T12:02:00+09:00",
            }
        ],
        "commands": [
            {
                "commandId": "cmd_1",
                "command": "uv run pytest",
                "workingDirectory": "%REPO_ROOT%",
                "exitCode": 1 if failed else 0,
                "status": "FAILED" if failed else "PASSED",
                "stdout": "test output",
                "stderr": "failure" if failed else "",
            }
        ],
        "changedFiles": [
            {
                "path": "apps/knowledge-viewer/src/App.tsx",
                "changeType": "modified",
                "addedLines": 42,
                "deletedLines": 8,
            }
        ],
        "tests": [
            {
                "testId": "test_1",
                "framework": "pytest",
                "status": "FAILED" if failed else "PASSED",
                "passed": 47 if failed else 48,
                "failed": 1 if failed else 0,
                "exitCode": 1 if failed else 0,
            }
        ],
        "attachments": [
            {
                "type": "patch",
                "name": "session.patch",
                "content": "diff --git a/App.tsx b/App.tsx\n+Capture Viewer\n",
            }
        ],
    }
    return {
        "schemaVersion": "1.0",
        "captureId": capture_id,
        "sourceType": "codex",
        "captureType": "development_session",
        "captureDevice": "windows",
        "captureMethod": "windows_codex_wrapper",
        "projectId": "autoknowledge-lite",
        "targetFolder": "40_Reference/Codex",
        "parentDocument": "doc_parent",
        "capturedAt": "2026-08-03T12:10:00+09:00",
        "deviceId": "windows-test",
        "contentHash": digest(json.dumps(payload, ensure_ascii=False)),
        "metadata": {},
        "payload": payload,
    }


def empty_envelope(capture_id: str) -> dict[str, object]:
    value = envelope(capture_id)
    payload = value["payload"]
    assert isinstance(payload, dict)
    payload.update(
        {
            "request": None,
            "summary": None,
            "messages": [],
            "commands": [],
            "changedFiles": [],
            "tests": [],
            "attachments": [],
        }
    )
    value["contentHash"] = digest(json.dumps(payload, ensure_ascii=False))
    return value


def test_list_filters_search_sort_and_cursor(tmp_path: Path) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_passed"))
    client.post("/api/v1/captures", json=envelope("cap_failed", failed=True))

    failed = client.get(
        "/api/v1/captures",
        params={
            "sourceType": "codex",
            "projectId": "autoknowledge-lite",
            "testStatus": "failed",
        },
    )
    searched = client.get(
        "/api/v1/captures", params={"q": "App.tsx", "sort": "relevance"}
    )
    first = client.get("/api/v1/captures", params={"limit": 1})
    second = client.get(
        "/api/v1/captures", params={"limit": 1, "cursor": first.json()["nextCursor"]}
    )

    assert [item["captureId"] for item in failed.json()["items"]] == ["cap_failed"]
    assert searched.json()["items"][0]["match"]["field"] == "파일"
    assert first.json()["hasMore"] is True
    assert (
        first.json()["items"][0]["captureId"] != second.json()["items"][0]["captureId"]
    )


def test_session_detail_children_diff_and_file_history(tmp_path: Path) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_session"))

    detail = client.get("/api/v1/captures/cap_session").json()
    commands = client.get("/api/v1/captures/cap_session/commands").json()
    diffs = client.get("/api/v1/captures/cap_session/diffs").json()
    history = client.get(
        "/api/v1/files/history",
        params={"path": "apps\\knowledge-viewer\\src\\App.tsx"},
    ).json()

    assert detail["commandsSummary"]["count"] == 1
    assert detail["testsSummary"]["status"] == "passed"
    assert commands["items"][0]["command"] == "uv run pytest"
    assert diffs["items"][0]["content"].startswith("diff --git")
    assert history["sessions"][0]["captureId"] == "cap_session"


def test_metadata_update_does_not_modify_collected_evidence(tmp_path: Path) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_metadata"))

    updated = client.patch(
        "/api/v1/captures/cap_metadata",
        json={"title": "사용자 제목", "tags": ["viewer"], "userNote": "첫 구조 확정"},
    ).json()
    message = client.get("/api/v1/captures/cap_metadata/messages").json()["items"][0]

    assert updated["capture"]["title"] == "사용자 제목"
    assert updated["userNote"] == "첫 구조 확정"
    assert message["content"] == "uv run pytest 명령으로 Viewer 테스트를 확인했습니다."


def test_capture_graph_uses_collected_files_tests_and_depth(tmp_path: Path) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_graph"))

    graph = client.get(
        "/api/v1/graph/neighborhood/cap_graph",
        params={"depth": 1},
    ).json()

    assert {node["type"] for node in graph["nodes"]} >= {
        "DEVELOPMENT_SESSION",
        "PROJECT",
        "TASK",
        "FILE",
        "COMMAND",
        "TEST_RESULT",
    }
    assert {edge["type"] for edge in graph["edges"]} >= {
        "belongs_to_project",
        "contains_task",
        "changed_file",
        "executed_command",
        "tested_by",
    }

    task_graph = client.get(
        "/api/v1/graph/neighborhood/task:cap_graph:session",
        params={"depth": 1},
    ).json()
    assert {edge["type"] for edge in task_graph["edges"]} >= {
        "contains_task",
        "modifies",
        "executes",
        "runs",
    }
    assert {edge["type"] for edge in graph["edges"]} >= {
        "changed_file",
        "executed_command",
        "tested_by",
    }

    compact = client.get(
        "/api/v1/graph",
        params={
            "nodeTypes": "DOCUMENT,PROJECT,CLIPBOARD_CAPTURE,DEVELOPMENT_SESSION,FILE"
        },
    ).json()
    node_ids = {node["id"] for node in compact["nodes"]}
    assert all(
        edge["from"] in node_ids and edge["to"] in node_ids for edge in compact["edges"]
    )


def test_knowledge_graph_includes_chatgpt_task_activity_chain(tmp_path: Path) -> None:
    save_chatgpt_projection(tmp_path)
    client = api(tmp_path)

    graph = client.get("/api/v1/graph").json()

    assert {node["type"] for node in graph["nodes"]} == {
        "CHATGPT_SESSION",
        "CHATGPT_MESSAGE",
        "TASK",
        "ACTIVITY",
    }
    assert {edge["type"] for edge in graph["edges"]} == {
        "contains_message",
        "contains_task",
        "contains_activity",
        "derived_from",
    }
    assert graph["warnings"] == []

    task_node = next(node for node in graph["nodes"] if node["type"] == "TASK")
    neighborhood = client.get(
        f"/api/v1/graph/neighborhood/{task_node['id']}", params={"depth": 1}
    ).json()
    assert {node["type"] for node in neighborhood["nodes"]} >= {
        "CHATGPT_SESSION",
        "TASK",
        "ACTIVITY",
    }

    filtered = client.get("/api/v1/graph", params={"sourceType": "codex"}).json()
    assert filtered["nodes"] == []


def test_document_backlinks_keep_capture_relation_type(tmp_path: Path) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_backlink"))

    response = client.get("/api/v1/documents/doc_parent/capture-backlinks")

    assert response.status_code == 200
    assert response.json()["items"][0]["captureId"] == "cap_backlink"
    assert response.json()["items"][0]["relationType"] == "parent_of"


def test_populated_session_tabs_reference_task_and_task_links_back(
    tmp_path: Path,
) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=envelope("cap_task_links"))

    detail = client.get("/api/v1/captures/cap_task_links").json()
    task = detail["tasks"][0]
    collections = {
        name: client.get(f"/api/v1/captures/cap_task_links/{path}").json()
        for name, path in {
            "messages": "messages",
            "changedFiles": "changed-files",
            "commands": "commands",
            "tests": "tests",
        }.items()
    }
    task_detail = client.get(f"/api/v1/tasks/{task['taskId']}").json()

    assert task["boundaryStatus"] == "suggested"
    assert task["provenance"]["derivedBy"] == "rule"
    assert all(
        values["items"][0]["taskId"] == task["taskId"]
        for values in collections.values()
    )
    assert task_detail["capture"]["captureId"] == "cap_task_links"
    assert set(task_detail["navigation"]) == {
        "overview",
        "messages",
        "changedFiles",
        "commands",
        "tests",
        "graph",
    }


def test_empty_session_returns_explicit_zero_counts_without_task(
    tmp_path: Path,
) -> None:
    client = api(tmp_path)
    client.post("/api/v1/captures", json=empty_envelope("cap_empty"))

    detail = client.get("/api/v1/captures/cap_empty").json()
    assert detail["messagesSummary"]["count"] == 0
    assert detail["changedFilesSummary"]["count"] == 0
    assert detail["commandsSummary"]["count"] == 0
    assert detail["testsSummary"] == {"count": 0, "status": "none"}
    assert detail["tasks"] == []
    for path in ("messages", "changed-files", "commands", "tests"):
        response = client.get(f"/api/v1/captures/cap_empty/{path}").json()
        assert response["items"] == []
        assert response["total"] == 0

    graph = client.get(
        "/api/v1/graph/neighborhood/cap_empty", params={"depth": 1}
    ).json()
    assert all(node["type"] != "TASK" for node in graph["nodes"])
    assert all(edge["type"] != "contains_task" for edge in graph["edges"])
