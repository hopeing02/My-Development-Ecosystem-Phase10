from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.chatgpt_import import ChatGPTImportService
from autoknowledge_lite.chatgpt_import_api import install_chatgpt_import_api
from autoknowledge_lite.store import JsonShareStore


def export_bytes() -> bytes:
    payload = [
        {
            "id": "api-session",
            "title": "API Import Session",
            "create_time": 1787011200.0,
            "update_time": 1787011260.0,
            "current_node": "message-node",
            "mapping": {
                "message-node": {
                    "parent": None,
                    "message": {
                        "id": "api-message",
                        "author": {"role": "user"},
                        "content": {"parts": ["API 원본"]},
                    },
                }
            },
        }
    ]
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(payload))
    return output.getvalue()


def client(tmp_path: Path) -> TestClient:
    data_dir = tmp_path / "chatgpt-data"
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "jobs"),
            auto_process=False,
            chatgpt_import_service=ChatGPTImportService(data_dir),
        )
    )


def test_import_api_requires_explicit_control_key_configuration(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_CONTROL_API_KEY", raising=False)

    response = client(tmp_path).post(
        "/api/v1/chatgpt/imports",
        content=export_bytes(),
        headers={"Content-Type": "application/zip"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHATGPT_IMPORT_API_DISABLED"


def test_import_api_rejects_missing_or_wrong_bearer_token(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    api = client(tmp_path)

    missing = api.post(
        "/api/v1/chatgpt/imports",
        content=export_bytes(),
        headers={"Content-Type": "application/zip"},
    )
    wrong = api.post(
        "/api/v1/chatgpt/imports",
        content=export_bytes(),
        headers={
            "Content-Type": "application/zip",
            "Authorization": "Bearer wrong",
        },
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert missing.json()["error"]["code"] == "UNAUTHORIZED"


def test_import_api_streams_zip_to_local_import_service_and_cleans_staging(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    api = client(tmp_path)

    response = api.post(
        "/api/v1/chatgpt/imports",
        content=export_bytes(),
        headers={
            "Content-Type": "application/zip",
            "Authorization": "Bearer local-secret",
            "X-File-Name": "my-chatgpt-export.zip",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "imported"
    assert body["discoveredSessions"] == 1
    assert body["projectedSessions"] == 1
    assert "rawArchivePath" not in body
    data_dir = tmp_path / "chatgpt-data"
    assert list((data_dir / "raw" / "chatgpt" / "imports").glob("*/export.zip"))
    incoming = data_dir / "incoming" / "chatgpt"
    assert not list(incoming.iterdir())


def test_import_api_rejects_non_zip_content_type_before_writing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")

    response = client(tmp_path).post(
        "/api/v1/chatgpt/imports",
        content=b"not a zip",
        headers={
            "Content-Type": "text/plain",
            "Authorization": "Bearer local-secret",
        },
    )

    assert response.status_code == 415
    assert response.json()["detail"]["code"] == (
        "CHATGPT_IMPORT_CONTENT_TYPE_UNSUPPORTED"
    )
    assert not (tmp_path / "chatgpt-data" / "incoming").exists()


def test_import_api_rejects_invalid_zip_and_cleans_staging(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")

    response = client(tmp_path).post(
        "/api/v1/chatgpt/imports",
        content=b"not a zip",
        headers={
            "Content-Type": "application/zip",
            "Authorization": "Bearer local-secret",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CHATGPT_EXPORT_INVALID_ZIP"
    incoming = tmp_path / "chatgpt-data" / "incoming" / "chatgpt"
    assert not list(incoming.iterdir())


def test_import_api_rejects_upload_over_configured_limit_before_staging(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    application = FastAPI()
    service = ChatGPTImportService(tmp_path / "chatgpt-data")
    install_chatgpt_import_api(application, service, max_upload_bytes=4)

    response = TestClient(application).post(
        "/api/v1/chatgpt/imports",
        content=b"too large",
        headers={
            "Content-Type": "application/zip",
            "Authorization": "Bearer local-secret",
        },
    )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "CHATGPT_IMPORT_UPLOAD_TOO_LARGE"
    assert not (tmp_path / "chatgpt-data" / "incoming").exists()
