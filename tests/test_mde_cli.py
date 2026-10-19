from __future__ import annotations

from pathlib import Path

import pytest

import mde_cli as mde


def test_save_command_parses_message() -> None:
    parser = mde.build_parser()

    args = parser.parse_args(["save", "-m", "feat: test"])

    assert args.command == "save"
    assert args.message == "feat: test"
    assert args.no_push is False


def test_save_command_parses_no_push() -> None:
    parser = mde.build_parser()

    args = parser.parse_args(["save", "-m", "feat: test", "--no-push"])

    assert args.command == "save"
    assert args.message == "feat: test"
    assert args.no_push is True


""" def test_main_runs_save_command(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_save(commit_message: str, push: bool) -> None:
        called["commit_message"] = commit_message
        called["push"] = push

    monkeypatch.setattr("mde.save", fake_save)

    exit_code = mde.main(["save", "-m", "feat: test", "--no-push"])

    assert exit_code == 0
    assert called == {"commit_message": "feat: test", "push": False}
 """


def test_new_command_parses_project_name() -> None:
    parser = mde.build_parser()

    args = parser.parse_args(["new", "autoknowledge-lite"])

    assert args.command == "new"
    assert args.project_name == "autoknowledge-lite"


""" def test_main_runs_new_command(monkeypatch: pytest.MonkeyPatch) -> None:
    created_paths = [
        Path("apps/autoknowledge-lite"),
        Path("docs/15_projects/autoknowledge-lite"),
    ]

    def fake_create_project(project_name: str) -> list[Path]:
        assert project_name == "autoknowledge-lite"
        return created_paths

    monkeypatch.setattr("mde.create_project", fake_create_project)

    exit_code = mde.main(["new", "autoknowledge-lite"])

    assert exit_code == 0


@pytest.mark.parametrize(
    "command",
    ["docs", "build", "release", "obsidian", "deploy"],
)
def test_reserved_commands_parse(command: str) -> None:
    parser = mde.build_parser()

    args = parser.parse_args([command])

    assert args.command == command


@pytest.mark.parametrize(
    "command",
    ["docs", "build", "release", "obsidian", "deploy"],
) """
""" def test_reserved_commands_return_reserved_status(command: str) -> None:
    assert mde.main([command]) == 2 """


def test_main_without_command_returns_error() -> None:
    exit_code = mde.main([])

    assert exit_code == 1


@pytest.mark.parametrize(
    "arguments",
    [
        ["generate", "--help"],
        ["generate", "command", "--help"],
        ["inbox", "--help"],
        ["inbox", "list", "--help"],
    ],
)
def test_reserved_command_help_is_explicit(arguments: list[str], capsys) -> None:
    with pytest.raises(SystemExit) as error:
        mde.main(arguments)

    assert error.value.code == 0
    output = capsys.readouterr().out.lower()
    assert "reserved" in output
    assert "not implemented" in output


@pytest.mark.parametrize(
    "arguments",
    [["generate"], ["generate", "command", "example"], ["inbox"], ["inbox", "list"]],
)
def test_reserved_commands_do_not_change_files(
    arguments: list[str], tmp_path: Path, monkeypatch, capsys
) -> None:
    manifest = tmp_path / "inbox" / "tasks" / "legacy" / "manifest.yaml"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b"existing legacy input must remain unchanged\n")
    before = {
        path.relative_to(tmp_path): path.read_bytes() if path.is_file() else None
        for path in tmp_path.rglob("*")
    }
    monkeypatch.chdir(tmp_path)

    assert mde.main(arguments) == 2

    output = capsys.readouterr().out
    assert "reserved but not implemented yet" in output
    assert "generated" not in output.lower()
    assert before == {
        path.relative_to(tmp_path): path.read_bytes() if path.is_file() else None
        for path in tmp_path.rglob("*")
    }
