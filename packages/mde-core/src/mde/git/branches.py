from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from mde.config.project import ProjectConfig
from mde.git.repository import current_branch, run_git

if TYPE_CHECKING:
    from mde.task.types import TaskDefinition


class BranchPolicyError(RuntimeError):
    """Raised when a task does not follow the configured branch policy."""


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-.")
    return cleaned.lower() or "task"


def branch_name_for_task(
    task_id: str,
    task_type: str = "task",
    *,
    assignee: str | None = None,
    pattern: str | None = None,
) -> str:
    if pattern is None:
        return (
            f"{_slug(task_type)}/{_slug(assignee)}/{_slug(task_id)}"
            if assignee
            else f"{_slug(task_type)}/{_slug(task_id)}"
        )
    if not assignee:
        raise BranchPolicyError("Task assignee is required by the project policy.")
    return pattern.format(
        type=_slug(task_type),
        assignee=_slug(assignee),
        task_id=_slug(task_id),
    )


def expected_branch_for_task(task: TaskDefinition, config: ProjectConfig) -> str:
    return branch_name_for_task(
        task.task_id,
        task.task_type,
        assignee=task.assignee,
        pattern=config.repository.branch_pattern,
    )


def validate_task_branch(
    task: TaskDefinition,
    config: ProjectConfig,
    *,
    active_branch: str | None = None,
) -> str:
    expected = expected_branch_for_task(task, config)
    if task.branch is not None and task.branch != expected:
        raise BranchPolicyError(
            f"Task branch mismatch: expected '{expected}', configured '{task.branch}'."
        )
    if active_branch is not None and active_branch != expected:
        raise BranchPolicyError(
            f"Active branch mismatch: expected '{expected}', active '{active_branch}'."
        )
    if (
        task.base_branch is not None
        and task.base_branch != config.repository.default_branch
    ):
        raise BranchPolicyError(
            "Task base branch mismatch: expected "
            f"'{config.repository.default_branch}', configured '{task.base_branch}'."
        )
    return expected


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
