from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.capture_api import (
    contains_sensitive_content,
    normalize_capture_text,
    server_content_hash,
)
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


class RecordingIndexer:
    def __init__(self) -> None:
        self.indexed: list[str] = []
        self.links: list[tuple[str, str]] = []

    def index_file(self, source: str, relative_path: str) -> dict[str, object]:
        self.indexed.append(relative_path)
        return {"documentId": f"ks-test::{relative_path}"}

    def search_documents(self, source: str, query: str, *, limit: int = 20):
        return ()

    def link_child(
        self, source: str, parent_document_id: str, target_document_id: str
    ) -> dict[str, object]:
        self.links.append((parent_document_id, target_document_id))
        return {"fileSaved": True}


def _hash(content: str) -> str:
    return hashlib.sha256(normalize_capture_text(content).encode()).hexdigest()


def _vectors(name: str) -> list[dict[str, object]]:
    path = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "capture-core"
        / "test-vectors"
        / name
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _request(
    content: str = "공통 Capture API가 저장할 충분한 길이의 한글 본문입니다.",
    *,
    capture_id: str = "cap_test_001",
    source_type: str = "chatgpt",
    target_folder: str = "40_Reference",
    parent_document: str | None = None,
) -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "captureId": capture_id,
        "sourceType": source_type,
        "captureType": "clipboard_item",
        "captureDevice": "android",
        "captureMethod": "android_clipboard",
        "projectId": "autoknowledge-lite",
        "targetFolder": target_folder,
        "parentDocument": parent_document,
        "capturedAt": "2026-08-02T21:20:00+09:00",
        "deviceId": "local-random-uuid",
        "contentHash": _hash(content),
        "metadata": {"sourceApp": "chatgpt_android"},
        "payload": {
            "content": content,
            "title": None,
            "mimeType": "text/plain",
            "language": "ko",
        },
    }


def _client(tmp_path: Path, indexer: RecordingIndexer | None = None) -> TestClient:
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "data"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            mde_client=indexer or RecordingIndexer(),
        )
    )


def test_capture_saves_markdown_with_source_and_parent_relation(tmp_path: Path) -> None:
    indexer = RecordingIndexer()
    client = _client(tmp_path, indexer)

    response = client.post(
        "/api/v1/captures",
        json=_request(parent_document="ks-parent::20_Learning/Parent.md"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "saved"
    assert body["captureId"] == "cap_test_001"
    assert body["captureType"] == "clipboard_item"
    assert body["duplicate"] is False
    path = tmp_path / "vault" / body["documentPath"]
    markdown = path.read_text(encoding="utf-8")
    assert 'source_type: "chatgpt"' in markdown
    assert 'capture_id: "cap_test_001"' in markdown
    assert "[[ks-parent::20_Learning/Parent.md]]" in markdown
    assert indexer.indexed == [body["documentPath"]]
    assert indexer.links == [("ks-parent::20_Learning/Parent.md", body["documentId"])]


def test_server_uses_shared_normalization_sensitive_and_hash_vectors() -> None:
    for vector in _vectors("normalization.json"):
        assert normalize_capture_text(str(vector["input"])) == vector["normalized"]
    for vector in _vectors("sensitive-content.json"):
        assert contains_sensitive_content(str(vector["input"])) is vector["sensitive"]
    for vector in _vectors("hashes.json"):
        normalized = normalize_capture_text(str(vector["input"]))
        assert normalized == vector["normalized"]
        assert server_content_hash(normalized) == vector["sha256"]
    for vector in _vectors("filenames.json"):
        captured_at = datetime.fromisoformat(str(vector["capturedAt"]))
        filename = (
            f"{captured_at.strftime('%Y-%m-%d-%H%M%S')}-"
            f"{vector['sourceType']}-clip-{str(vector['contentHash'])[:8]}.md"
        )
        assert filename == vector["filename"]


def test_content_duplicate_and_capture_id_idempotency_are_distinct(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    original = _request()

    saved = client.post("/api/v1/captures", json=original)
    replay = client.post("/api/v1/captures", json=original)
    duplicate = client.post(
        "/api/v1/captures",
        json=_request(capture_id="cap_test_002", source_type="codex"),
    )
    conflicting = _request(content="서로 다른 본문", capture_id="cap_test_001")
    conflict = client.post("/api/v1/captures", json=conflicting)

    assert replay.json() == saved.json()
    assert duplicate.json()["status"] == "duplicate"
    assert duplicate.json()["documentId"] == saved.json()["documentId"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "DUPLICATE_CAPTURE_ID"
    assert len(list((tmp_path / "vault" / "40_Reference").glob("*.md"))) == 1


def test_server_hash_wins_and_reports_mismatch(tmp_path: Path) -> None:
    client = _client(tmp_path)
    request = _request()
    request["contentHash"] = "0" * 64

    response = client.post("/api/v1/captures", json=request)

    assert response.status_code == 200
    assert response.json()["warnings"] == ["CONTENT_HASH_MISMATCH"]


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("schemaVersion", "2.0", "INVALID_SCHEMA_VERSION"),
        ("sourceType", "email", "INVALID_SOURCE_TYPE"),
        ("captureType", "unknown", "INVALID_CAPTURE_TYPE"),
        ("captureDevice", "ios", "INVALID_CAPTURE_DEVICE"),
    ],
)
def test_invalid_envelope_fields_return_standard_errors(
    tmp_path: Path, field: str, value: str, code: str
) -> None:
    request = _request()
    request[field] = value

    response = _client(tmp_path).post("/api/v1/captures", json=request)

    assert response.status_code == 422
    assert response.json()["status"] == "error"
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("folder", ["../outside", "C:\\Vault", "/absolute"])
def test_target_folder_cannot_escape_vault(tmp_path: Path, folder: str) -> None:
    response = _client(tmp_path).post(
        "/api/v1/captures", json=_request(target_folder=folder)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TARGET_FOLDER"
    assert not (tmp_path / "outside").exists()


def test_symlink_target_folder_cannot_escape_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    try:
        (vault / "40_Reference").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")

    response = _client(tmp_path).post("/api/v1/captures", json=_request())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_TARGET_FOLDER"
    assert list(outside.iterdir()) == []


def test_sensitive_content_is_blocked_without_echoing_secret(tmp_path: Path) -> None:
    secret = "Authorization: Bearer abcdefghijklmnop"
    response = _client(tmp_path).post("/api/v1/captures", json=_request(content=secret))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SENSITIVE_CONTENT_DETECTED"
    assert secret not in response.text
    assert contains_sensitive_content(secret)


def test_development_session_is_saved_and_idempotent(
    tmp_path: Path,
) -> None:
    request = _request()
    request.update(
        {
            "captureId": "cap_session_001",
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "captureMethod": "windows_codex_session",
            "payload": {
                "sourceSessionId": "session-1",
                "clientType": "codex_app",
                "startedAt": "2026-08-02T20:00:00+09:00",
                "endedAt": "2026-08-02T21:00:00+09:00",
                "repository": {
                    "name": "My-Development-Ecosystem",
                    "rootAlias": "%REPO_ROOT%",
                    "branch": "main",
                    "headBefore": "abc123",
                    "headAfter": "def456",
                    "worktreePathAlias": "%REPO_ROOT%",
                },
                "messages": [],
                "commands": [],
                "changedFiles": [],
                "tests": [],
                "attachments": [
                    {
                        "type": "patch",
                        "name": "session.patch",
                        "content": "diff --git a/a.txt b/a.txt\n",
                    }
                ],
            },
        }
    )

    client = _client(tmp_path)
    response = client.post("/api/v1/captures", json=request)
    replay = client.post("/api/v1/captures", json=request)

    assert response.status_code == 200
    assert response.json()["status"] == "saved"
    assert response.json()["revision"] == 1
    assert replay.status_code == 200
    assert replay.json() == response.json()
    document = tmp_path / "vault" / response.json()["documentPath"]
    assert document.is_file()
    assert "Codex 작업" in document.read_text(encoding="utf-8")
    assert (document.with_suffix("") / "session.patch").is_file()


def test_development_session_changed_replay_creates_revision(tmp_path: Path) -> None:
    request = _request()
    request.update(
        {
            "captureId": "cap_session_revision",
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "captureMethod": "windows_codex_wrapper",
            "payload": {
                "captureSessionId": "cap_session_revision",
                "sourceSessionId": None,
                "clientType": "codex_wrapper",
                "title": "Revision test",
                "startedAt": "2026-08-02T20:00:00+09:00",
                "endedAt": "2026-08-02T21:00:00+09:00",
                "messages": [],
                "commands": [],
                "changedFiles": [],
                "tests": [],
                "attachments": [],
            },
        }
    )
    client = _client(tmp_path)

    first = client.post("/api/v1/captures", json=request)
    request["payload"]["summary"] = "Additional progress"
    second = client.post("/api/v1/captures", json=request)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["revision"] == 2
    assert "SESSION_REVISION_CREATED" in second.json()["warnings"]
    assert first.json()["documentPath"] != second.json()["documentPath"]


def test_legacy_android_share_uses_common_handler_and_keeps_response(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    content = "기존 Android APK가 전송하는 클립보드 본문입니다."

    response = client.post(
        "/v1/share",
        json={
            "content": content,
            "capture_origin": "android_clipboard",
            "source_type": "general",
            "source_app": "android_clipboard",
            "content_hash": _hash(content),
            "captured_at": "2026-08-02T21:20:00+09:00",
            "device_id": "legacy-device",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    record = JsonShareStore(tmp_path / "data").load(response.json()["job_id"])
    assert record.document_id is not None
    assert record.note_path is not None
    assert (tmp_path / "vault" / record.note_path).is_file()
