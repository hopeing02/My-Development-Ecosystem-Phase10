from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from autoknowledge_lite.ai import AnalysisError, DeterministicKnowledgeAnalyzer
from autoknowledge_lite.api import create_app
from autoknowledge_lite.models import ShareRecord
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore, ShareStoreError


def client_for(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "jobs"),
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
        )
    )


def test_status_reports_service_version(tmp_path: Path) -> None:
    response = client_for(tmp_path).get("/v1/status")

    assert response.status_code == 200
    assert response.json() == {
        "service": "autoknowledge-lite",
        "status": "ok",
        "version": "0.2.1",
    }


def test_pc_capture_page_has_fixed_safe_folder_options(tmp_path: Path) -> None:
    response = client_for(tmp_path).get("/pc")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.count("<option value=") == 6
    for folder in (
        "00_Inbox",
        "10_Life",
        "20_Learning",
        "30_Interests",
        "40_Reference",
        "90_Archive",
    ):
        assert f'<option value="{folder}">' in response.text
    assert 'fetch("/v1/share"' in response.text
    assert 'name="target_folder"' in response.text
    assert 'type="text" name="target_folder"' not in response.text


def test_android_apk_download_serves_only_configured_file(tmp_path: Path) -> None:
    apk_path = tmp_path / "autoknowledge-lite.apk"
    apk_path.write_bytes(b"safe-apk")
    client = TestClient(
        create_app(
            JsonShareStore(tmp_path / "jobs"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            android_apk_path=apk_path,
        )
    )

    response = client.get("/downloads/autoknowledge-lite.apk")

    assert response.status_code == 200
    assert response.content == b"safe-apk"
    assert response.headers["content-type"] == "application/vnd.android.package-archive"
    assert "autoknowledge-lite-v0.2.0.apk" in response.headers["content-disposition"]


def test_android_apk_download_returns_not_found_when_build_is_missing(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            JsonShareStore(tmp_path / "jobs"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            android_apk_path=tmp_path / "missing.apk",
        )
    )

    response = client.get("/downloads/autoknowledge-lite.apk")

    assert response.status_code == 404
    assert response.json() == {"detail": "Android APK is not available."}


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

    client = TestClient(create_app(FailingStore(tmp_path / "jobs"), auto_process=False))

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
    client = TestClient(create_app(store, FailingAnalyzer(), auto_process=False))
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
    assert "## Summary" in markdown
    assert "## Key Points" in markdown
    assert "## Original Content\n\nFirst point. Second point." in markdown
    stored = json.loads(
        (tmp_path / "jobs" / f"{accepted['job_id']}.json").read_text(encoding="utf-8")
    )
    assert stored["markdown"] == markdown
    note_path = Path(response.json()["note_path"])
    assert note_path.is_file()
    assert note_path.read_text(encoding="utf-8") == markdown
    assert stored["note_path"] == str(note_path)


def test_markdown_requires_analysis(tmp_path: Path) -> None:
    client = client_for(tmp_path)
    accepted = client.post("/v1/share", json={"content": "Queued"}).json()

    response = client.post("/v1/markdown", json={"job_id": accepted["job_id"]})

    assert response.status_code == 409
    assert response.json() == {"detail": "Share job must be analyzed first."}


def test_share_automatically_analyzes_and_renders_markdown(tmp_path: Path) -> None:
    class RecordingSync:
        def __init__(self) -> None:
            self.paths: list[Path] = []

        def sync(self, note_path: Path) -> None:
            self.paths.append(note_path)

    store = JsonShareStore(tmp_path / "jobs")
    git_sync = RecordingSync()
    client = TestClient(
        create_app(
            store,
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=True,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            git_sync=git_sync,
        )
    )

    response = client.post(
        "/v1/share",
        json={"title": "Automatic Note", "content": "First fact. Second fact."},
    )

    assert response.status_code == 202
    stored = store.load(response.json()["job_id"])
    assert stored.status == "processed"
    assert stored.analysis is not None
    assert stored.markdown is not None
    assert stored.note_path is not None
    assert Path(stored.note_path).is_file()
    assert "# Automatic Note" in stored.markdown
    assert git_sync.paths == [Path(stored.note_path)]


def test_share_fetches_url_only_content_before_automatic_analysis(
    tmp_path: Path,
) -> None:
    class FakeFetcher:
        def fetch(self, url: str) -> str:
            assert url == "https://example.com/article"
            return "Fetched article body. Important second fact."

    store = JsonShareStore(tmp_path / "jobs")
    client = TestClient(
        create_app(
            store,
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=True,
            content_fetcher=FakeFetcher(),
            note_store=ObsidianNoteStore(tmp_path / "vault"),
        )
    )

    response = client.post(
        "/v1/share",
        json={
            "content": "https://example.com/article",
            "source_url": "https://example.com/article",
        },
    )

    stored = store.load(response.json()["job_id"])
    assert stored.content == "Fetched article body. Important second fact."
    assert stored.analysis is not None
    assert stored.analysis.summary.startswith("Fetched article body.")
    assert stored.markdown is not None
