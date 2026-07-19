from pathlib import Path

import pytest

from mde.git.repository import GitError, ensure_branch_write_allowed


def write_project_config(root: Path) -> None:
    directory = root / ".mde"
    directory.mkdir()
    (directory / "project.yaml").write_text(
        """version: 1
project:
  id: sample
  name: Sample
repository:
  default_branch: main
  branch_pattern: "{type}/{assignee}/{task_id}"
  protected_branches: [main]
commands:
  test: []
  build: []
""",
        encoding="utf-8",
    )


def test_rejects_protected_branch(tmp_path: Path) -> None:
    write_project_config(tmp_path)

    with pytest.raises(GitError, match="protected branch 'main'"):
        ensure_branch_write_allowed(tmp_path, branch="main")


def test_allows_task_branch(tmp_path: Path) -> None:
    write_project_config(tmp_path)

    assert (
        ensure_branch_write_allowed(tmp_path, branch="feature/github-user/task-001")
        == "feature/github-user/task-001"
    )
