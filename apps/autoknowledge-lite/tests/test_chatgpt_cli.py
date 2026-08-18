from __future__ import annotations

import json
import zipfile
from pathlib import Path

from autoknowledge_lite.cli import main


def conversation(
    session_id: str, *, title: str | None = "CLI Session"
) -> dict[str, object]:
    return {
        "id": session_id,
        "title": title,
        "create_time": 1787011200.0,
        "update_time": 1787011260.0,
        "current_node": "message-node",
        "mapping": {
            "message-node": {
                "parent": None,
                "message": {
                    "id": f"{session_id}-message",
                    "author": {"role": "user"},
                    "content": {"parts": ["원본"]},
                },
            }
        },
    }


def write_export(path: Path, records: list[dict[str, object]]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("conversations.json", json.dumps(records))


def test_chatgpt_import_cli_archives_and_projects_export(
    tmp_path: Path, capsys
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    data_dir = tmp_path / "data"
    write_export(archive_path, [conversation("session-1")])

    exit_code = main(["chatgpt-import", str(archive_path), "--data-dir", str(data_dir)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "imported"
    assert output["discoveredSessions"] == 1
    assert output["projectedSessions"] == 1
    assert output["failedSessions"] == 0
    assert output["warnings"] == []
    assert "rawArchivePath" not in output
    assert list((data_dir / "raw" / "chatgpt" / "imports").glob("*/export.zip"))


def test_chatgpt_import_cli_reports_partial_without_losing_raw_archive(
    tmp_path: Path, capsys
) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    data_dir = tmp_path / "data"
    write_export(
        archive_path,
        [conversation("valid"), conversation("missing-title", title=None)],
    )

    exit_code = main(["chatgpt-import", str(archive_path), "--data-dir", str(data_dir)])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "partial"
    assert output["projectedSessions"] == 1
    assert output["failedSessions"] == 1
    assert output["warnings"][0]["code"] == "CHATGPT_SESSION_TITLE_MISSING"
    assert list((data_dir / "raw" / "chatgpt" / "imports").glob("*/export.zip"))


def test_chatgpt_import_cli_reports_duplicate_import(tmp_path: Path, capsys) -> None:
    archive_path = tmp_path / "chatgpt-export.zip"
    data_dir = tmp_path / "data"
    write_export(archive_path, [conversation("session-1")])
    arguments = ["chatgpt-import", str(archive_path), "--data-dir", str(data_dir)]

    assert main(arguments) == 0
    capsys.readouterr()
    exit_code = main(arguments)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["status"] == "duplicate"
    assert output["rawDuplicate"] is True
    assert output["duplicateSessions"] == 1


def test_chatgpt_import_cli_returns_structured_error_for_missing_zip(
    tmp_path: Path, capsys
) -> None:
    exit_code = main(
        [
            "chatgpt-import",
            str(tmp_path / "missing.zip"),
            "--data-dir",
            str(tmp_path / "data"),
        ]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["status"] == "error"
    assert output["error"]["code"] == "CHATGPT_EXPORT_NOT_FOUND"
