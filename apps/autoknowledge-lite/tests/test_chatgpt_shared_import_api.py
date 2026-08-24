from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.chatgpt_shared_archive import (
    ChatGPTSharedFetchError,
    ChatGPTSharedSnapshot,
)
from autoknowledge_lite.chatgpt_shared_import import ChatGPTSharedImportService
from autoknowledge_lite.chatgpt_shared_import_api import (
    install_chatgpt_shared_import_api,
)
from autoknowledge_lite.store import JsonShareStore

SHARE_ID = "12345678-abcd-4321-abcd-1234567890ab"
SHARE_URL = f"https://chatgpt.com/share/{SHARE_ID}"


class FakeFetcher:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def fetch(self, shared_url: str) -> ChatGPTSharedSnapshot:
        return ChatGPTSharedSnapshot(
            shared_url=shared_url,
            share_id=SHARE_ID,
            content=self.content,
            content_type="text/html",
            snapshot_sha256=hashlib.sha256(self.content).hexdigest(),
        )


class FailingFetcher:
    def fetch(self, _: str) -> ChatGPTSharedSnapshot:
        raise ChatGPTSharedFetchError(
            "CHATGPT_SHARED_FETCH_FAILED", "Shared link could not be retrieved"
        )


def shared_html() -> bytes:
    record = {
        "id": SHARE_ID,
        "title": "API shared session",
        "create_time": 1_700_000_000,
        "update_time": 1_700_000_100,
        "current_node": "message-1",
        "mapping": {
            "message-1": {
                "parent": None,
                "message": {
                    "id": "message-1",
                    "author": {"role": "user"},
                    "content": {"parts": ["API original"]},
                },
            }
        },
    }
    embedded = json.dumps({"conversation": record})
    return f"<script>self.__next_f.push([1,{json.dumps(embedded)}])</script>".encode()


def api_client(tmp_path: Path, content: bytes | None = None) -> TestClient:
    service = ChatGPTSharedImportService(
        tmp_path / "data", fetcher=FakeFetcher(content or shared_html())
    )
    application = FastAPI()
    install_chatgpt_shared_import_api(application, service)
    return TestClient(application)


def headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer local-secret",
    }


def test_requires_control_key_before_reading_link(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_CONTROL_API_KEY", raising=False)

    response = api_client(tmp_path).post(
        "/api/v1/chatgpt/shared-imports", json={"url": SHARE_URL}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CHATGPT_IMPORT_API_DISABLED"


def test_imports_explicit_link_without_returning_url_or_raw_path(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")

    response = api_client(tmp_path).post(
        "/api/v1/chatgpt/shared-imports", json={"url": SHARE_URL}, headers=headers()
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "imported"
    assert body["projectedSessions"] == 1
    assert "rawArchivePath" not in body
    assert SHARE_URL not in response.text
    assert list(
        (tmp_path / "data" / "raw" / "chatgpt" / "shared").glob("*/snapshot.html")
    )


def test_returns_partial_after_archiving_damaged_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")

    response = api_client(tmp_path, b"<html>damaged</html>").post(
        "/api/v1/chatgpt/shared-imports", json={"url": SHARE_URL}, headers=headers()
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["failedSessions"] == 1
    assert response.json()["warnings"][0]["code"] == (
        "CHATGPT_SHARED_CONVERSATION_MISSING"
    )
    assert list(
        (tmp_path / "data" / "raw" / "chatgpt" / "shared").glob("*/snapshot.html")
    )


def test_rejects_invalid_url_without_reflecting_it(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    application = FastAPI()
    install_chatgpt_shared_import_api(
        application, ChatGPTSharedImportService(tmp_path / "data")
    )
    invalid = "https://chatgpt.com.evil.test/share/private-token"

    response = TestClient(application).post(
        "/api/v1/chatgpt/shared-imports",
        json={"url": invalid},
        headers=headers(),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CHATGPT_SHARED_URL_INVALID"
    assert invalid not in response.text


def test_maps_upstream_failure_without_leaking_link(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    application = FastAPI()
    install_chatgpt_shared_import_api(
        application,
        ChatGPTSharedImportService(tmp_path / "data", fetcher=FailingFetcher()),
    )

    response = TestClient(application).post(
        "/api/v1/chatgpt/shared-imports",
        json={"url": SHARE_URL},
        headers=headers(),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "CHATGPT_SHARED_FETCH_FAILED"
    assert SHARE_URL not in response.text


def test_create_app_installs_shared_import_route(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "local-secret")
    service = ChatGPTSharedImportService(
        tmp_path / "data", fetcher=FakeFetcher(shared_html())
    )
    application = create_app(
        JsonShareStore(tmp_path / "jobs"),
        auto_process=False,
        chatgpt_shared_import_service=service,
    )

    response = TestClient(application).post(
        "/api/v1/chatgpt/shared-imports",
        json={"url": SHARE_URL},
        headers=headers(),
    )

    assert response.status_code == 200
