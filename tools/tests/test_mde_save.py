from __future__ import annotations

import pytest

from tools.mde_save import (
    SaveError,
    build_parser,
    ensure_has_changes,
    get_changed_files,
    get_current_branch,
    save,
)


class FakeResult:
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout


def test_parser_requires_commit_message() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_accepts_commit_message() -> None:
    parser = build_parser()

    args = parser.parse_args(["-m", "feat: test save"])

    assert args.message == "feat: test save"
    assert args.no_push is False


def test_parser_accepts_no_push() -> None:
    parser = build_parser()

    args = parser.parse_args(["-m", "feat: test save", "--no-push"])

    assert args.message == "feat: test save"
    assert args.no_push is True


def test_get_current_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        assert command == ["git", "branch", "--show-current"]
        return FakeResult(stdout="main")

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    assert get_current_branch() == "main"


def test_get_current_branch_fails_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        assert command == ["git", "branch", "--show-current"]
        return FakeResult(stdout="")

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    with pytest.raises(SaveError):
        get_current_branch()


def test_get_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        assert command == ["git", "status", "--short"]
        return FakeResult(stdout=" M README.md\n?? mde.py")

    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    assert get_changed_files() == [" M README.md", "?? mde.py"]


def test_ensure_has_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_changed_files(
        logger: object | None = None,
    ) -> list[str]:
        return [" M README.md"]

    monkeypatch.setattr("tools.mde_save.get_changed_files", fake_get_changed_files)

    assert ensure_has_changes() == [" M README.md"]


def test_ensure_has_changes_fails_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_changed_files(
        logger: object | None = None,
    ) -> list[str]:
        return []

    monkeypatch.setattr("tools.mde_save.get_changed_files", fake_get_changed_files)

    with pytest.raises(SaveError):
        ensure_has_changes()


def test_save_runs_expected_commands_without_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_get_current_branch(
        logger: object | None = None,
    ) -> str:
        return "main"

    def fake_ensure_has_changes(
        logger: object | None = None,
    ) -> list[str]:
        return [" M README.md"]

    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        commands.append(command)
        return FakeResult(stdout="ok")

    monkeypatch.setattr("tools.mde_save.get_current_branch", fake_get_current_branch)
    monkeypatch.setattr("tools.mde_save.ensure_has_changes", fake_ensure_has_changes)
    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    save(commit_message="feat: test save", push=False)

    assert commands == [
        ["uv", "run", "black", "."],
        ["uv", "run", "ruff", "check", "."],
        ["uv", "run", "pytest"],
        ["git", "add", "."],
        ["git", "commit", "-m", "feat: test save"],
    ]


def test_save_runs_expected_commands_with_push(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_get_current_branch(
        logger: object | None = None,
    ) -> str:
        return "main"

    def fake_ensure_has_changes(
        logger: object | None = None,
    ) -> list[str]:
        return [" M README.md"]

    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        commands.append(command)
        return FakeResult(stdout="ok")

    monkeypatch.setattr("tools.mde_save.get_current_branch", fake_get_current_branch)
    monkeypatch.setattr("tools.mde_save.ensure_has_changes", fake_ensure_has_changes)
    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    save(commit_message="feat: test save", push=True)

    assert commands[-1] == ["git", "push"]


def test_save_stops_when_command_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_current_branch(
        logger: object | None = None,
    ) -> str:
        return "main"

    def fake_ensure_has_changes(
        logger: object | None = None,
    ) -> list[str]:
        return [" M README.md"]

    def fake_run_required(
        command: list[str],
        logger: object | None = None,
    ) -> FakeResult:
        if command == ["uv", "run", "black", "."]:
            raise SaveError("Command failed: uv run black .")
        return FakeResult(stdout="ok")

    monkeypatch.setattr("tools.mde_save.get_current_branch", fake_get_current_branch)
    monkeypatch.setattr("tools.mde_save.ensure_has_changes", fake_ensure_has_changes)
    monkeypatch.setattr("tools.mde_save.run_required", fake_run_required)

    with pytest.raises(SaveError):
        save(commit_message="feat: test save", push=True)
