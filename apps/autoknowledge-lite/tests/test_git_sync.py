from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from autoknowledge_lite.git_sync import GitNoteSync, GitSyncError


def test_disabled_sync_does_not_require_git_repository(tmp_path: Path) -> None:
    GitNoteSync(tmp_path, enabled=False).sync(tmp_path / "missing.md")


def test_sync_pulls_commits_and_pushes_only_requested_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "vault"
    note = repo / "AutoKnowledge" / "note.md"
    (repo / ".git").mkdir(parents=True)
    note.parent.mkdir()
    note.write_text("# Note", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return_code = 1 if "diff" in command else 0
        return subprocess.CompletedProcess(command, return_code, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    GitNoteSync(repo, enabled=True).sync(note)

    operations = [command[3:] for command in commands]
    assert operations == [
        ["pull", "--rebase", "origin", "main"],
        ["add", "--", "AutoKnowledge/note.md"],
        ["diff", "--cached", "--quiet"],
        ["commit", "-m", "knowledge: add note"],
        ["push", "origin", "main"],
    ]


def test_sync_rejects_note_outside_vault(tmp_path: Path) -> None:
    repo = tmp_path / "vault"
    (repo / ".git").mkdir(parents=True)
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside", encoding="utf-8")

    with pytest.raises(GitSyncError, match="outside"):
        GitNoteSync(repo, enabled=True).sync(outside)
