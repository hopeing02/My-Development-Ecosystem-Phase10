from pathlib import Path

import pytest

from mde.git.repository import GitError, ensure_clean_worktree


def test_clean_worktree_accepts_no_changes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("mde.git.repository.changed_files", lambda root: ())
    ensure_clean_worktree(tmp_path)


def test_clean_worktree_rejects_changes(monkeypatch, tmp_path: Path):
    monkeypatch.setattr("mde.git.repository.changed_files", lambda root: (" M file.py",))
    with pytest.raises(GitError, match="not clean"):
        ensure_clean_worktree(tmp_path)
