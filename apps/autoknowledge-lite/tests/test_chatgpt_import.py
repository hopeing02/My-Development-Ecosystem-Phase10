from __future__ import annotations

import json
import zipfile
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from autoknowledge_lite.chatgpt_archive import ChatGPTArchiveStore
from autoknowledge_lite.chatgpt_import import (
    ChatGPTImportError,
    ChatGPTImportService,
    ChatGPTIssueStore,
    ChatGPTProjectionStore,
)
from autoknowledge_lite.knowledge_model import MessageRole


def fixed_clock() -> datetime:
    return datetime.fromisoformat("2026-08-18T16:00:00+09:00")


def conversation(
    session_id: str,
    *,
    title: str | None = "실제 ChatGPT 세션",
    answer: str = "원본 답변",
) -> dict[str, object]:
    value: dict[str, object] = {
        "id": session_id,
        "title": title,
        "create_time": 1787011200.0,
        "update_time": 1787011260.0,
        "current_node": "assistant-node",
        "mapping": {
            "root": {"parent": None, "message": None},
            "user-node": {
                "parent": "root",
                "message": {
                    "id": f"{session_id}-user",
                    "author": {"role": "user"},
                    "create_time": 1787011201.0,
                    "content": {"parts": [" 원본 질문 "]},
                },
            },
            "assistant-node": {
                "parent": "user-node",
                "message": {
                    "id": f"{session_id}-assistant",
                    "author": {"role": "assistant"},
                    "create_time": 1787011202.0,
                    "content": {"parts": [answer]},
                },
            },
        },
    }
    return value


def write_export(path: Path, records: list[dict[str, object]]) -> bytes:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(records))
    return path.read_bytes()


def service(data_dir: Path) -> ChatGPTImportService:
    return ChatGPTImportService(
        data_dir,
        archive_store=ChatGPTArchiveStore(data_dir, clock=fixed_clock),
        projection_store=ChatGPTProjectionStore(data_dir, clock=fixed_clock),
    )


def test_archives_and_projects_valid_sessions_while_isolating_invalid_session(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    records = [conversation("valid"), conversation("invalid", title=None)]
    original_records = deepcopy(records)
    original_zip = write_export(archive_path, records)

    result = service(tmp_path / "data").import_export(archive_path)

    assert result.discovered_sessions == 2
    assert result.projected_sessions == 1
    assert result.failed_sessions == 1
    assert result.duplicate_sessions == 0
    assert [issue.code for issue in result.issues] == ["CHATGPT_SESSION_TITLE_MISSING"]
    assert result.issue_report_path is not None
    assert ChatGPTIssueStore.load(result.issue_report_path).issues == result.issues
    revision = result.revisions[0].record
    assert revision.session_id == "valid"
    assert revision.revision == 1
    assert revision.adapter_version == "1.1.0"
    assert revision.projection.messages[0].role == MessageRole.USER
    assert revision.projection.messages[0].content == " 원본 질문 "
    assert result.raw_archive_path.read_bytes() == original_zip
    assert archive_path.read_bytes() == original_zip
    with zipfile.ZipFile(archive_path) as archive:
        assert json.loads(archive.read("conversations.json")) == original_records


def test_persists_partial_message_warnings_without_losing_valid_content(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    record = conversation("partial")
    mapping = record["mapping"]
    assert isinstance(mapping, dict)
    assistant = mapping["assistant-node"]
    assert isinstance(assistant, dict)
    message = assistant["message"]
    assert isinstance(message, dict)
    message["create_time"] = "invalid"
    message["contentHash"] = "INVALID"
    write_export(archive_path, [record])

    result = service(tmp_path / "data").import_export(archive_path)

    assert result.projected_sessions == 1
    assert result.failed_sessions == 0
    assert {issue.code for issue in result.issues} == {
        "CHATGPT_MESSAGE_HASH_INVALID",
        "CHATGPT_MESSAGE_TIMESTAMP_INVALID",
    }
    assert result.issue_report_path is not None
    projection = result.revisions[0].record.projection
    assert projection.messages[1].content == "원본 답변"
    assert projection.messages[1].timestamp is None
    assert projection.messages[1].content_hash is None


def test_reimporting_same_export_does_not_create_another_revision(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(archive_path, [conversation("session-1")])
    importer = service(tmp_path / "data")

    first = importer.import_export(archive_path)
    second = importer.import_export(archive_path)

    assert first.raw_duplicate is False
    assert second.raw_duplicate is True
    assert second.projected_sessions == 0
    assert second.duplicate_sessions == 1
    assert second.revisions[0].revision == 1
    revision_dir = second.revisions[0].revision_path.parent
    assert [path.name for path in revision_dir.glob("revision-*.json")] == [
        "revision-0001.json"
    ]


def test_changed_same_session_creates_next_revision_and_preserves_first(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    first_path = tmp_path / "first.zip"
    second_path = tmp_path / "second.zip"
    write_export(first_path, [conversation("session-1", answer="첫 답변")])
    write_export(second_path, [conversation("session-1", answer="수정 답변")])
    importer = service(data_dir)

    first = importer.import_export(first_path)
    second = importer.import_export(second_path)

    assert first.revisions[0].revision == 1
    assert second.revisions[0].revision == 2
    assert first.revisions[0].revision_path.exists()
    assert second.revisions[0].revision_path.exists()
    loaded_first = ChatGPTProjectionStore.load(first.revisions[0].revision_path)
    loaded_second = ChatGPTProjectionStore.load(second.revisions[0].revision_path)
    assert loaded_first.projection.messages[1].content == "첫 답변"
    assert loaded_second.projection.messages[1].content == "수정 답변"


def test_corrupt_existing_revision_is_not_overwritten(tmp_path: Path) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(archive_path, [conversation("session-1")])
    importer = service(tmp_path / "data")
    first = importer.import_export(archive_path)
    first.revisions[0].revision_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ChatGPTImportError) as captured:
        importer.import_export(archive_path)

    assert captured.value.code == "CHATGPT_PROJECTION_REVISION_INVALID"
    assert first.revisions[0].revision_path.read_text(encoding="utf-8") == "{}"
