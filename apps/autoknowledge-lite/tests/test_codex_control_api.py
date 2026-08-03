from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


class NullIndexer:
    def index_file(self, source: str, relative_path: str):
        return {"documentId": relative_path}

    def search_documents(self, source: str, query: str, *, limit: int = 20):
        return ()

    def link_child(self, source: str, parent_document_id: str, target_document_id: str):
        return {}


class FakeCodexController:
    def __init__(self) -> None:
        self.attached = False
        self.synced = False

    def doctor(self):
        return [{"name": "app_server", "status": "ok", "path": "C:/Users/private"}]

    def list_projects(self):
        return [
            {
                "projectId": "mde",
                "displayName": "MDE",
                "repositoryPath": "C:/Users/private/repo",
                "enabled": True,
            }
        ]

    def discover_codex_sessions(self):
        return [
            {
                "sourceSessionId": "source-1",
                "clientType": "codex_app_server",
                "title": "Public title",
                "updatedAt": "2026-08-03T12:00:00+09:00",
                "_sourceCwd": "C:/Users/private/repo",
            }
        ]

    def inspect_codex_session(self, source_session_id: str):
        return {
            "sourceSessionId": source_session_id,
            "title": "Public title",
            "messages": 12,
            "assistantMessages": 6,
            "toolEvents": 2,
        }

    def start(self, project_id: str, title: str, request=None):
        return {
            "captureSessionId": "cap-1",
            "state": "CAPTURING",
            "repositoryRoot": "C:/Users/private/repo",
            "messages": [],
        }

    def attach_codex_session(
        self,
        capture_session_id: str,
        source_session_id: str,
        *,
        consent: bool,
        client_type: str = "codex_app_server",
    ):
        self.attached = consent
        return {"sourceSessionId": source_session_id}

    def sync_codex_session(self, capture_session_id: str, *, transmit: bool = True):
        self.synced = True
        return {
            "captureSessionId": capture_session_id,
            "newMessages": 12,
            "totalMessages": 12,
            "transmitted": transmit,
        }

    def finalize(
        self,
        *,
        session_id=None,
        summary=None,
        closure_reason="manual_finalize",
        transmit=True,
    ):
        return {
            "captureSessionId": session_id,
            "sourceSessionId": "source-1",
            "state": "SAVED",
            "messages": [{}] * 12,
            "serverResult": {
                "revision": 2,
                "documentId": "doc-1",
                "documentPath": "40_Reference/session.md",
            },
        }

    def load_session(self, session_id: str):
        return self.finalize(session_id=session_id)


def make_client(tmp_path: Path, controller: FakeCodexController) -> TestClient:
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "data"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            mde_client=NullIndexer(),
            codex_controller=controller,
        )
    )


def test_control_api_is_disabled_without_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_CONTROL_API_KEY", raising=False)
    response = make_client(tmp_path, FakeCodexController()).get("/api/v1/mobile/status")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CONTROL_API_DISABLED"


def test_control_api_requires_bearer_key_and_hides_paths(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "mobile-secret")
    client = make_client(tmp_path, FakeCodexController())
    assert client.get("/api/v1/mobile/codex/sessions").status_code == 401

    response = client.get(
        "/api/v1/mobile/codex/sessions",
        headers={"Authorization": "Bearer mobile-secret"},
    )

    assert response.status_code == 200
    serialized = response.text
    assert "source-1" in serialized
    assert "C:/Users" not in serialized
    assert "mobile-secret" not in serialized


def test_mobile_attach_requires_explicit_consent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "mobile-secret")
    controller = FakeCodexController()
    client = make_client(tmp_path, controller)
    headers = {"Authorization": "Bearer mobile-secret"}

    denied = client.post(
        "/api/v1/mobile/codex/captures/cap-1/attach",
        headers=headers,
        json={"sourceSessionId": "source-1", "consent": False},
    )
    accepted = client.post(
        "/api/v1/mobile/codex/captures/cap-1/attach",
        headers=headers,
        json={"sourceSessionId": "source-1", "consent": True},
    )

    assert denied.status_code == 422
    assert accepted.status_code == 200
    assert controller.attached is True


def test_mobile_capture_sync_finalize_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "mobile-secret")
    monkeypatch.setenv("AUTOKNOWLEDGE_VIEWER_URL", "http://100.75.235.67:8765")
    controller = FakeCodexController()
    client = make_client(tmp_path, controller)
    headers = {"Authorization": "Bearer mobile-secret"}

    started = client.post(
        "/api/v1/mobile/codex/captures",
        headers=headers,
        json={"projectId": "mde", "title": "Mobile capture"},
    )
    synced = client.post(
        "/api/v1/mobile/codex/captures/cap-1/sync",
        headers=headers,
        json={"transmit": True},
    )
    finalized = client.post(
        "/api/v1/mobile/codex/captures/cap-1/finalize",
        headers=headers,
        json={"transmit": True},
    )

    assert started.json() == {
        "captureSessionId": "cap-1",
        "state": "CAPTURING",
        "messageCount": 0,
        "revision": None,
        "documentId": None,
        "documentPath": None,
        "viewerUrl": "http://100.75.235.67:8765",
    }
    assert synced.json()["totalMessages"] == 12
    assert finalized.json()["state"] == "SAVED"
    assert finalized.json()["revision"] == 2
    assert finalized.json()["viewerUrl"] == (
        "http://100.75.235.67:8765/"
        "?sourceId=autoknowledge-vault&documentId=doc-1"
    )
