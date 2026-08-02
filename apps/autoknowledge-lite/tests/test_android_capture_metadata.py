from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from autoknowledge_lite.ai import DeterministicKnowledgeAnalyzer
from autoknowledge_lite.api import create_app
from autoknowledge_lite.markdown import render_markdown
from autoknowledge_lite.models import KnowledgeAnalysis, ShareRecord
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


class NoOpIndexer:
    def index_file(self, source: str, relative_path: str) -> dict[str, object]:
        return {}

    def search_documents(
        self, source: str, query: str, *, limit: int = 20
    ) -> tuple[object, ...]:
        return ()

    def link_child(
        self, source: str, parent_document_id: str, target_document_id: str
    ) -> dict[str, object]:
        return {}


def test_share_persists_android_capture_metadata(tmp_path) -> None:
    store = JsonShareStore(tmp_path / "jobs")
    client = TestClient(
        create_app(
            store,
            analyzer=DeterministicKnowledgeAnalyzer(),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            mde_client=NoOpIndexer(),
        )
    )
    content_hash = "a" * 64

    response = client.post(
        "/v1/share",
        json={
            "content": "Android에서 복사한 Codex 답변",
            "target_folder": "40_Reference",
            "capture_origin": "android_clipboard",
            "source_type": "codex",
            "source_app": "codex_remote_android",
            "content_hash": content_hash,
            "captured_at": "2026-08-02T20:43:00+09:00",
            "device_id": "local-device",
        },
    )

    assert response.status_code == 202
    record = store.load(response.json()["job_id"])
    assert record.source_type == "codex"
    assert record.source_app == "codex_remote_android"
    assert record.content_hash == content_hash
    assert record.device_id == "local-device"


def test_android_capture_markdown_and_filename_include_capture_metadata(
    tmp_path,
) -> None:
    record = ShareRecord(
        job_id="12345678-0000-0000-0000-000000000000",
        received_at=datetime(2026, 8, 2, 11, 43, tzinfo=timezone.utc),
        captured_at=datetime(2026, 8, 2, 20, 43, tzinfo=timezone.utc),
        content="복사한 실제 답변",
        title="Codex 답변",
        target_folder="40_Reference",
        capture_origin="android_clipboard",
        source_type="codex",
        source_app="codex_remote_android",
        content_hash="f6bd37ca" + "0" * 56,
        analysis=KnowledgeAnalysis(
            summary="Codex 답변",
            key_points=["핵심"],
            tags=["codex"],
            provider="local",
        ),
    )

    markdown = render_markdown(record)
    path = ObsidianNoteStore(tmp_path / "vault").save(record, markdown)

    assert 'source_type: "codex"' in markdown
    assert 'source_app: "codex_remote_android"' in markdown
    assert 'content_hash: "f6bd37ca' in markdown
    assert "parent_document: null" in markdown
    assert path.name == "2026-08-02-204300-codex-clip-f6bd37ca.md"
