from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from autoknowledge_lite.ai import DeterministicKnowledgeAnalyzer
from autoknowledge_lite.api import create_app
from autoknowledge_lite.models import (
    ALLOWED_VAULT_FOLDERS,
    DEFAULT_VAULT_FOLDER,
    ShareRecord,
    ShareRequest,
)
from autoknowledge_lite.obsidian import ObsidianNoteStore, ObsidianStoreError
from autoknowledge_lite.store import JsonShareStore


def record_for(folder: str = DEFAULT_VAULT_FOLDER) -> ShareRecord:
    return ShareRecord(
        job_id="12345678-0000-0000-0000-000000000000",
        received_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        content="개인 지식",
        title="폴더 선택",
        target_folder=folder,
    )


def test_request_defaults_to_inbox() -> None:
    request = ShareRequest(content="content")

    assert request.target_folder == "00_Inbox"


@pytest.mark.parametrize("folder", ALLOWED_VAULT_FOLDERS)
def test_request_accepts_allowed_folder(folder: str) -> None:
    request = ShareRequest(content="content", target_folder=folder)

    assert request.target_folder == folder


@pytest.mark.parametrize(
    "folder",
    ["../outside", "C:\\private", "/absolute", "AutoKnowledge", "unknown"],
)
def test_request_rejects_unapproved_folder(folder: str) -> None:
    with pytest.raises(ValidationError):
        ShareRequest(content="content", target_folder=folder)


def test_existing_record_without_folder_defaults_to_inbox() -> None:
    record = ShareRecord.model_validate(
        {
            "job_id": "12345678-0000-0000-0000-000000000000",
            "received_at": "2026-07-23T00:00:00Z",
            "content": "legacy",
        }
    )

    assert record.target_folder == "00_Inbox"


@pytest.mark.parametrize("folder", ALLOWED_VAULT_FOLDERS)
def test_note_store_saves_only_in_selected_folder(tmp_path: Path, folder: str) -> None:
    path = ObsidianNoteStore(tmp_path / "vault").save(record_for(folder), "# note")

    assert path.parent == (tmp_path / "vault" / folder).resolve()
    assert path.read_text(encoding="utf-8") == "# note"


def test_note_store_defends_against_unvalidated_folder(tmp_path: Path) -> None:
    unsafe = ShareRecord.model_construct(
        job_id="12345678-0000-0000-0000-000000000000",
        received_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
        content="unsafe",
        target_folder="../outside",
    )

    with pytest.raises(ObsidianStoreError, match="Unsupported"):
        ObsidianNoteStore(tmp_path / "vault").save(unsafe, "# unsafe")

    assert not (tmp_path / "outside").exists()


def test_api_persists_folder_and_syncs_selected_note(tmp_path: Path) -> None:
    class RecordingSync:
        def __init__(self) -> None:
            self.paths: list[Path] = []

        def sync(self, note_path: Path) -> None:
            self.paths.append(note_path)

    store = JsonShareStore(tmp_path / "jobs")
    sync = RecordingSync()
    client = TestClient(
        create_app(
            store,
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=True,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            git_sync=sync,
        )
    )

    response = client.post(
        "/v1/share",
        json={
            "content": "Learning note. Second fact.",
            "title": "Selected folder",
            "target_folder": "20_Learning",
        },
    )

    assert response.status_code == 202
    stored = store.load(response.json()["job_id"])
    note_path = Path(stored.note_path or "")
    assert stored.target_folder == "20_Learning"
    assert note_path.parent == (tmp_path / "vault" / "20_Learning").resolve()
    assert sync.paths == [note_path]


def test_api_rejects_path_traversal_without_writing(tmp_path: Path) -> None:
    store = JsonShareStore(tmp_path / "jobs")
    client = TestClient(
        create_app(
            store,
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
        )
    )

    response = client.post(
        "/v1/share",
        json={"content": "unsafe", "target_folder": "../outside"},
    )

    assert response.status_code == 422
    assert list((tmp_path / "jobs").glob("*.json")) == []
    assert not (tmp_path / "outside").exists()
