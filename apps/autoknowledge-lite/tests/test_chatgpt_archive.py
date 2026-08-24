from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from autoknowledge_lite.chatgpt_archive import (
    ChatGPTArchiveError,
    ChatGPTArchiveStore,
)
from autoknowledge_lite.chatgpt_session_source import ChatGPTExportSource


def export_zip(path: Path, records: list[dict[str, object]]) -> bytes:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(records))
    return path.read_bytes()


def conversation(session_id: str) -> dict[str, object]:
    return {
        "id": session_id,
        "title": "보관할 ChatGPT 세션",
        "create_time": 1787011200.0,
        "update_time": 1787011260.0,
        "mapping": {},
        "current_node": None,
    }


def fixed_clock() -> datetime:
    return datetime.fromisoformat("2026-08-18T15:00:00+09:00")


def test_archives_original_zip_and_manifest_outside_vault_without_mutating_source(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source" / "chatgpt-export.zip"
    source_path.parent.mkdir()
    original = export_zip(source_path, [conversation("session-1")])
    discovery = ChatGPTExportSource(source_path).discover_sessions()
    data_dir = tmp_path / "local-data"

    result = ChatGPTArchiveStore(data_dir, clock=fixed_clock).archive(discovery)

    assert result.duplicate is False
    assert result.archive_path.read_bytes() == original
    assert source_path.read_bytes() == original
    assert result.archive_path.is_relative_to(data_dir / "raw" / "chatgpt" / "imports")
    assert "vault" not in result.archive_path.parts
    manifest = ChatGPTArchiveStore.load_manifest(result.manifest_path)
    assert manifest.archive_sha256 == discovery.archive_sha256
    assert manifest.archive_size == len(original)
    assert manifest.original_filename == "chatgpt-export.zip"
    assert manifest.session_count == 1
    assert manifest.imported_at == fixed_clock()
    assert manifest.source_members == ("conversations.json",)
    assert ChatGPTExportSource(result.archive_path).discover_sessions().sessions


def test_same_archive_is_idempotent_and_reuses_original_manifest(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "chatgpt-export.zip"
    export_zip(source_path, [conversation("session-1")])
    discovery = ChatGPTExportSource(source_path).discover_sessions()
    store = ChatGPTArchiveStore(tmp_path / "data", clock=fixed_clock)

    first = store.archive(discovery)
    second = store.archive(discovery)

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.import_id == first.import_id
    assert second.manifest == first.manifest
    assert len(list(store.imports_dir.glob("chatgpt_*"))) == 1


def test_manifest_records_discovery_warning_codes(tmp_path: Path) -> None:
    source_path = tmp_path / "chatgpt-export.zip"
    export_zip(
        source_path,
        [conversation("session-1"), conversation("session-1"), {"title": "ID 없음"}],
    )
    discovery = ChatGPTExportSource(source_path).discover_sessions()

    result = ChatGPTArchiveStore(tmp_path / "data", clock=fixed_clock).archive(
        discovery
    )

    assert result.manifest.warning_count == 2
    assert result.manifest.warning_codes == (
        "CHATGPT_EXPORT_SESSION_ID_DUPLICATE",
        "CHATGPT_EXPORT_SESSION_ID_MISSING",
    )


def test_rejects_source_changed_after_discovery_without_partial_archive(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "chatgpt-export.zip"
    export_zip(source_path, [conversation("session-1")])
    discovery = ChatGPTExportSource(source_path).discover_sessions()
    source_path.write_bytes(source_path.read_bytes() + b"changed")
    store = ChatGPTArchiveStore(tmp_path / "data", clock=fixed_clock)

    with pytest.raises(ChatGPTArchiveError) as captured:
        store.archive(discovery)

    assert captured.value.code == "CHATGPT_ARCHIVE_SOURCE_CHANGED"
    assert not store.imports_dir.exists()


def test_rejects_corrupt_existing_import_instead_of_overwriting_it(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "chatgpt-export.zip"
    export_zip(source_path, [conversation("session-1")])
    discovery = ChatGPTExportSource(source_path).discover_sessions()
    store = ChatGPTArchiveStore(tmp_path / "data", clock=fixed_clock)
    first = store.archive(discovery)
    first.manifest_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ChatGPTArchiveError) as captured:
        store.archive(discovery)

    assert captured.value.code == "CHATGPT_ARCHIVE_MANIFEST_INVALID"
    assert first.archive_path.exists()


def test_rejects_naive_archive_clock_before_writing(tmp_path: Path) -> None:
    source_path = tmp_path / "chatgpt-export.zip"
    export_zip(source_path, [conversation("session-1")])
    discovery = ChatGPTExportSource(source_path).discover_sessions()
    store = ChatGPTArchiveStore(
        tmp_path / "data", clock=lambda: datetime(2026, 8, 18, 15, 0)
    )

    with pytest.raises(ChatGPTArchiveError) as captured:
        store.archive(discovery)

    assert captured.value.code == "CHATGPT_ARCHIVE_CLOCK_INVALID"
    assert not store.imports_dir.exists()
