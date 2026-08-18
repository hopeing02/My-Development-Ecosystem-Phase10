from __future__ import annotations

import hashlib
import json
from pathlib import Path

from autoknowledge_lite.chatgpt_shared_archive import ChatGPTSharedSnapshot
from autoknowledge_lite.chatgpt_shared_import import ChatGPTSharedImportService
from autoknowledge_lite.knowledge_model import DataSource

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


def conversation(content: str = "Original request") -> dict[str, object]:
    return {
        "id": SHARE_ID,
        "title": "Shared implementation",
        "create_time": 1_700_000_000,
        "update_time": 1_700_000_100,
        "current_node": "message-1",
        "mapping": {
            "message-1": {
                "parent": None,
                "message": {
                    "id": "message-1",
                    "author": {"role": "user"},
                    "create_time": 1_700_000_000,
                    "content": {"parts": [content]},
                },
            }
        },
    }


def snapshot_html(content: str = "Original request") -> bytes:
    embedded = json.dumps({"conversation": conversation(content)})
    return f"<script>self.__next_f.push([1,{json.dumps(embedded)}])</script>".encode()


def test_archives_before_projecting_original_session(tmp_path: Path) -> None:
    original = snapshot_html()
    service = ChatGPTSharedImportService(tmp_path, fetcher=FakeFetcher(original))

    result = service.import_shared_link(SHARE_URL)

    assert result.projected_sessions == 1
    assert result.failed_sessions == 0
    assert result.raw_archive_path.read_bytes() == original
    projection = result.revisions[0].record.projection
    assert projection.session.provenance.source == DataSource.ORIGINAL
    assert projection.messages[0].content == "Original request"
    assert projection.messages[0].provenance.source == DataSource.ORIGINAL


def test_deduplicates_same_snapshot_and_projection(tmp_path: Path) -> None:
    service = ChatGPTSharedImportService(tmp_path, fetcher=FakeFetcher(snapshot_html()))

    first = service.import_shared_link(SHARE_URL)
    second = service.import_shared_link(SHARE_URL)

    assert first.raw_duplicate is False
    assert second.raw_duplicate is True
    assert second.projected_sessions == 0
    assert second.duplicate_sessions == 1
    assert second.revisions[0].revision == 1


def test_updated_shared_snapshot_creates_session_revision(tmp_path: Path) -> None:
    first = ChatGPTSharedImportService(
        tmp_path, fetcher=FakeFetcher(snapshot_html("First"))
    ).import_shared_link(SHARE_URL)
    second = ChatGPTSharedImportService(
        tmp_path, fetcher=FakeFetcher(snapshot_html("Updated"))
    ).import_shared_link(SHARE_URL)

    assert first.revisions[0].revision == 1
    assert second.revisions[0].revision == 2
    assert second.revisions[0].record.projection.messages[0].content == "Updated"


def test_preserves_damaged_snapshot_and_isolates_projection_warning(
    tmp_path: Path,
) -> None:
    damaged = b"<html>no structured conversation</html>"
    service = ChatGPTSharedImportService(tmp_path, fetcher=FakeFetcher(damaged))

    result = service.import_shared_link(SHARE_URL)

    assert result.discovered_sessions == 0
    assert result.failed_sessions == 1
    assert result.issues[0].code == "CHATGPT_SHARED_CONVERSATION_MISSING"
    assert result.issue_report_path is not None
    assert result.raw_archive_path.read_bytes() == damaged


def test_missing_required_original_field_fails_without_fabricating_data(
    tmp_path: Path,
) -> None:
    incomplete = conversation()
    del incomplete["title"]
    payload = {"conversation": incomplete}
    content = json.dumps(payload).encode()

    result = ChatGPTSharedImportService(
        tmp_path, fetcher=FakeFetcher(content)
    ).import_shared_link(SHARE_URL)

    assert result.projected_sessions == 0
    assert result.failed_sessions == 1
    assert result.issues[0].code == "CHATGPT_SESSION_TITLE_MISSING"
