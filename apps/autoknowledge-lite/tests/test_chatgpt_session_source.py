from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from autoknowledge_lite.chatgpt_session_source import (
    ChatGPTExportSource,
    ChatGPTSessionSourceError,
)


def write_export(path: Path, members: dict[str, object | str]) -> bytes:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in members.items():
            content = value if isinstance(value, str) else json.dumps(value)
            archive.writestr(name, content)
    return path.read_bytes()


def conversation(
    session_id: str, title: str = "실제 ChatGPT 세션"
) -> dict[str, object]:
    return {
        "id": session_id,
        "title": title,
        "create_time": 1787011200.0,
        "update_time": 1787011260.0,
        "mapping": {},
        "current_node": None,
    }


def test_discovers_and_reads_sessions_without_extracting_or_mutating_zip(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    original = write_export(
        archive_path,
        {
            "export/conversations.json": [
                conversation("session-1"),
                conversation("session-2", "두 번째 세션"),
            ],
            "export/chat.html": "<html></html>",
        },
    )

    source = ChatGPTExportSource(archive_path)
    discovery = source.discover_sessions()
    record = source.read_session(discovery.sessions[1])

    assert discovery.archive_path == archive_path.resolve()
    assert discovery.archive_sha256 == hashlib.sha256(original).hexdigest()
    assert [item.source_session_id for item in discovery.sessions] == [
        "session-1",
        "session-2",
    ]
    assert discovery.sessions[1].title == "두 번째 세션"
    assert record["id"] == "session-2"
    assert archive_path.read_bytes() == original
    assert not (tmp_path / "export").exists()
    assert discovery.warnings == ()


def test_discovers_numbered_conversation_files_and_deduplicates_session_ids(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(
        archive_path,
        {
            "conversations-1.json": [conversation("session-1")],
            "conversations_2.json": [
                conversation("session-1", "중복"),
                conversation("session-2"),
            ],
        },
    )

    discovery = ChatGPTExportSource(archive_path).discover_sessions()

    assert [item.source_session_id for item in discovery.sessions] == [
        "session-1",
        "session-2",
    ]
    assert [warning.code for warning in discovery.warnings] == [
        "CHATGPT_EXPORT_SESSION_ID_DUPLICATE"
    ]


def test_isolates_damaged_json_and_invalid_records_as_warnings(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(
        archive_path,
        {
            "conversations-1.json": "{broken",
            "conversations-2.json": [
                "not-an-object",
                {"title": "ID 없음"},
                conversation("valid-session"),
            ],
        },
    )

    discovery = ChatGPTExportSource(archive_path).discover_sessions()

    assert [item.source_session_id for item in discovery.sessions] == ["valid-session"]
    assert discovery.sessions[0].source_index == 2
    assert [warning.code for warning in discovery.warnings] == [
        "CHATGPT_EXPORT_CONVERSATIONS_INVALID",
        "CHATGPT_EXPORT_SESSION_RECORD_INVALID",
        "CHATGPT_EXPORT_SESSION_ID_MISSING",
    ]


@pytest.mark.parametrize(
    "member_name", ["../conversations.json", "C:\\conversations.json"]
)
def test_rejects_unsafe_member_paths(tmp_path: Path, member_name: str) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(archive_path, {member_name: [conversation("session-1")]})

    with pytest.raises(ChatGPTSessionSourceError) as captured:
        ChatGPTExportSource(archive_path).discover_sessions()

    assert captured.value.code == "CHATGPT_EXPORT_UNSAFE_MEMBER_PATH"


def test_rejects_archive_over_uncompressed_size_limit(tmp_path: Path) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(archive_path, {"conversations.json": [conversation("session-1")]})

    with pytest.raises(ChatGPTSessionSourceError) as captured:
        ChatGPTExportSource(
            archive_path, max_total_uncompressed_bytes=10
        ).discover_sessions()

    assert captured.value.code == "CHATGPT_EXPORT_UNCOMPRESSED_TOO_LARGE"


def test_rejects_duplicate_member_paths(tmp_path: Path) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    with pytest.warns(UserWarning, match="Duplicate name"):
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("conversations.json", "[]")
            archive.writestr("conversations.json", "[]")

    with pytest.raises(ChatGPTSessionSourceError) as captured:
        ChatGPTExportSource(archive_path).discover_sessions()

    assert captured.value.code == "CHATGPT_EXPORT_MEMBER_DUPLICATE"


def test_reports_archive_without_conversations_json(tmp_path: Path) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    write_export(archive_path, {"chat.html": "<html></html>"})

    with pytest.raises(ChatGPTSessionSourceError) as captured:
        ChatGPTExportSource(archive_path).discover_sessions()

    assert captured.value.code == "CHATGPT_EXPORT_CONVERSATIONS_MISSING"


def test_reports_missing_or_non_export_archives(tmp_path: Path) -> None:
    with pytest.raises(ChatGPTSessionSourceError) as missing:
        ChatGPTExportSource(tmp_path / "missing.zip").discover_sessions()
    assert missing.value.code == "CHATGPT_EXPORT_NOT_FOUND"

    invalid_path = tmp_path / "invalid.zip"
    invalid_path.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ChatGPTSessionSourceError) as invalid:
        ChatGPTExportSource(invalid_path).discover_sessions()
    assert invalid.value.code == "CHATGPT_EXPORT_INVALID_ZIP"
