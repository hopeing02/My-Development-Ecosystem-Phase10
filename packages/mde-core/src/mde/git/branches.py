from __future__ import annotations

import re
from pathlib import Path

from mde.git.repository import current_branch, run_git


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return cleaned.lower() or "task"


def branch_name_for_task(task_id: str, task_type: str = "task") -> str:
    return f"{_slug(task_type)}/{_slug(task_id)}"


def local_branch_exists(branch: str, repository_root: Path) -> bool:
    output = run_git("branch", "--list", branch, repository_root=repository_root)
    return bool(output.strip())


def remote_branch_exists(
    branch: str, repository_root: Path, remote: str = "origin"
) -> bool:
    output = run_git(
        "branch", "-r", "--list", f"{remote}/{branch}", repository_root=repository_root
    )
    return bool(output.strip())


def checkout_branch(branch: str, repository_root: Path) -> None:
    run_git("checkout", branch, repository_root=repository_root)


def create_task_branch(
    branch: str,
    *,
    base_branch: str,
    repository_root: Path,
    remote: str = "origin",
) -> None:
    if local_branch_exists(branch, repository_root):
        checkout_branch(branch, repository_root)
        return
    if remote_branch_exists(branch, repository_root, remote):
        run_git(
            "checkout",
            "-b",
            branch,
            "--track",
            f"{remote}/{branch}",
            repository_root=repository_root,
        )
        return
    if current_branch(repository_root) != base_branch:
        checkout_branch(base_branch, repository_root)
    run_git("checkout", "-b", branch, repository_root=repository_root)
