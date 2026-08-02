import json
from pathlib import Path

from mde.cli import main


def _json_output(capsys) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_json_integration_contract_indexes_one_file(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "vault"
    note = source / "생활" / "자동화.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntags: [생활, 자동화]\n---\n# 생활 자동화\n[[점검 목록]]",
        encoding="utf-8",
    )
    monkeypatch.setenv("MDE_DATA_HOME", str(tmp_path / "data"))
    assert (
        main(
            [
                "knowledge",
                "add",
                str(source),
                "--name",
                "personal",
                "--category",
                "personal",
                "--type",
                "obsidian",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["knowledge", "integration-info", "--format", "json"]) == 0
    info = _json_output(capsys)
    assert info["apiVersion"] == "1"
    assert info["success"] is True
    assert info["capabilities"] == ["list-sources", "source-path", "index-file"]

    assert main(["knowledge", "list", "--format", "json"]) == 0
    sources = _json_output(capsys)["sources"]
    assert sources == [
        {
            "id": "ks-001",
            "name": "personal",
            "category": "personal",
            "sourceType": "obsidian",
            "enabled": True,
            "sensitive": True,
            "writableByCaptureApp": True,
        }
    ]
    assert "path" not in sources[0]

    assert main(["knowledge", "source-path", "personal", "--format", "json"]) == 0
    source_payload = _json_output(capsys)["source"]
    assert source_payload["path"] == str(source.resolve())

    command = [
        "knowledge",
        "index-file",
        "--source",
        "personal",
        "--path",
        "생활/자동화.md",
        "--format",
        "json",
    ]
    assert main(command) == 0
    result = _json_output(capsys)["result"]
    assert result == {
        "sourceId": "ks-001",
        "sourceName": "personal",
        "documentId": "ks-001::생활/자동화.md",
        "relativePath": "생활/자동화.md",
        "indexed": True,
        "status": "added",
        "title": "생활 자동화",
        "tagCount": 2,
        "linkCount": 1,
        "warningCount": 0,
        "warnings": [],
    }

    assert main(command) == 0
    unchanged = _json_output(capsys)["result"]
    assert unchanged["indexed"] is False
    assert unchanged["status"] == "unchanged"


def test_index_file_rejects_source_escape_with_structured_error(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "vault"
    source.mkdir()
    (tmp_path / "outside.md").write_text("# private", encoding="utf-8")
    monkeypatch.setenv("MDE_DATA_HOME", str(tmp_path / "data"))
    assert (
        main(
            [
                "knowledge",
                "add",
                str(source),
                "--name",
                "docs",
                "--category",
                "development",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        main(
            [
                "knowledge",
                "index-file",
                "--source",
                "docs",
                "--path",
                "../outside.md",
                "--format",
                "json",
            ]
        )
        == 1
    )
    payload = _json_output(capsys)
    assert payload["apiVersion"] == "1"
    assert payload["success"] is False
    assert payload["error"]["code"] == "PATH_OUTSIDE_SOURCE"


def test_sensitive_capture_write_requires_confirmation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    source = tmp_path / "work"
    source.mkdir()
    monkeypatch.setenv("MDE_DATA_HOME", str(tmp_path / "data"))
    assert (
        main(
            [
                "knowledge",
                "add",
                str(source),
                "--name",
                "work",
                "--category",
                "work",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert main(["knowledge", "update", "work", "--capture-write", "true"]) == 1
    assert "confirm-sensitive-write" in capsys.readouterr().out
    assert (
        main(
            [
                "knowledge",
                "update",
                "work",
                "--capture-write",
                "true",
                "--confirm-sensitive-write",
            ]
        )
        == 0
    )
