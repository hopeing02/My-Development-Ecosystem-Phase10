from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from autoknowledge_lite.ai import AnalysisError
from autoknowledge_lite.api import create_app
from autoknowledge_lite.models import ShareRecord
from autoknowledge_lite.store import JsonShareStore, ShareStoreError


def client_for(tmp_path: Path) -> TestClient:
    return TestClient(create_app(JsonShareStore(tmp_path / "jobs")))


def test_status_reports_service_version(tmp_path: Path) -> None:
    response = client_for(tmp_path).get("/v1/status")

    assert response.status_code == 200
    assert response.json() == {
        "service": "autoknowledge-lite",
        "status": "ok",
        "version": "0.1.0",
    }


def test_share_accepts_and_persists_valid_content(tmp_path: Path) -> None:
    response = client_for(tmp_path).post(
        "/v1/share",
        json={
            "content": "  A useful shared article.  ",
            "title": "  Example  ",
            "source_url": "https://example.com/article",
        },
    )

    assert response.status_code == 202
    body = response.json()
    UUID(body["job_id"])
    assert body["status"] == "queued"

    stored_path = tmp_path / "jobs" / f"{body['job_id']}.json"
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored["content"] == "A useful shared article."
    assert stored["title"] == "Example"
    assert stored["source_url"] == "https://example.com/article"
    assert stored["status"] == "queued"


def test_share_rejects_blank_content(tmp_path: Path) -> None:
    response = client_for(tmp_path).post("/v1/share", json={"content": "   "})

    assert response.status_code == 422
    assert list((tmp_path / "jobs").glob("*.json")) == []


def test_share_rejects_invalid_source_url(tmp_path: Path) -> None:
    response = client_for(tmp_path).post(
        "/v1/share",
        json={"content": "Valid content", "source_url": "not-a-url"},
    )

    assert response.status_code == 422


def test_share_returns_safe_error_when_storage_fails(tmp_path: Path) -> None:
    class FailingStore(JsonShareStore):
        def save(self, record: ShareRecord) -> Path:
            raise ShareStoreError("private storage detail")

    client = TestClient(create_app(FailingStore(tmp_path / "jobs")))

    response = client.post("/v1/share", json={"content": "Valid content"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to accept shared content."}
    assert "private storage detail" not in response.text


def test_process_analyzes_and_persists_share_job(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    accepted = client.post(
        "/v1/share",
        json={
            "title": "Python Knowledge",
            "content": "Python supports readable code. Python has type hints. Tests protect behavior.",
        },
    ).json()

    response = client.post("/v1/ai/process", json={"job_id": accepted["job_id"]})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "processed"
    assert body["analysis"]["provider"] == "local-deterministic"
    assert body["analysis"]["summary"].startswith("Python supports readable code.")
    assert "python" in body["analysis"]["tags"]

    stored_path = tmp_path / "jobs" / f"{accepted['job_id']}.json"
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    assert stored["status"] == "processed"
    assert stored["processed_at"] is not None
    assert stored["analysis"] == body["analysis"]


def test_process_returns_not_found_for_unknown_job(tmp_path: Path) -> None:
    response = client_for(tmp_path).post(
        "/v1/ai/process",
        json={"job_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Share job not found."}


def test_process_rejects_non_uuid_job_id(tmp_path: Path) -> None:
    response = client_for(tmp_path).post(
        "/v1/ai/process",
        json={"job_id": "../private"},
    )

    assert response.status_code == 422


def test_process_returns_safe_error_when_analysis_fails(tmp_path: Path) -> None:
    class FailingAnalyzer:
        def analyze(self, record: ShareRecord):
            raise AnalysisError("private provider detail")

    store = JsonShareStore(tmp_path / "jobs")
    client = TestClient(create_app(store, FailingAnalyzer()))
    accepted = client.post("/v1/share", json={"content": "Valid content"}).json()

    response = client.post("/v1/ai/process", json={"job_id": accepted["job_id"]})

    assert response.status_code == 502
    assert response.json() == {"detail": "Unable to analyze shared content."}
    assert "private provider detail" not in response.text


def test_markdown_renders_and_persists_analyzed_job(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    accepted = client.post(
        "/v1/share",
        json={"title": "Knowledge Note", "content": "First point. Second point."},
    ).json()
    client.post("/v1/ai/process", json={"job_id": accepted["job_id"]})

    response = client.post("/v1/markdown", json={"job_id": accepted["job_id"]})

    assert response.status_code == 200
    markdown = response.json()["markdown"]
    assert markdown.startswith("---\n")
    assert "# Knowledge Note" in markdown
    assert "## Key Points" in markdown
    stored = json.loads(
        (tmp_path / "jobs" / f"{accepted['job_id']}.json").read_text(encoding="utf-8")
    )
    assert stored["markdown"] == markdown


def test_markdown_requires_analysis(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    accepted = client.post("/v1/share", json={"content": "Queued"}).json()

    response = client.post("/v1/markdown", json={"job_id": accepted["job_id"]})

    assert response.status_code == 409
    assert response.json() == {"detail": "Share job must be analyzed first."}
