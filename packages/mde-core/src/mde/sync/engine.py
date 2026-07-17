from __future__ import annotations

from pathlib import Path
from typing import Callable

from mde.git import repository as git
from mde.git.branches import branch_name_for_task, create_task_branch, checkout_branch
from mde.sync.models import SyncPolicy, SyncResult
from mde.task.executor import execute_task
from mde.task.store import TaskStore
from mde.task.summary import write_mobile_summary


class SyncError(RuntimeError):
    """Raised when a Mobile Sync cycle cannot complete safely."""


TaskRunner = Callable[..., object]


def _commit_task_if_needed(
    root: Path, task, policy: SyncPolicy, branch: str
) -> tuple[str | None, bool]:
    if not policy.auto_commit or (
        policy.respect_task_policy and not task.execution.auto_save
    ):
        return None, False
    changes = git.changed_files(root)
    if not changes:
        return None, False
    git.add(repository_root=root)
    commit_hash = git.commit(
        f"chore(task): complete {task.task_id}", repository_root=root
    )
    pushed = False
    if policy.auto_push and (
        not policy.respect_task_policy or task.execution.auto_push
    ):
        git.push(remote=policy.remote, branch=branch, repository_root=root)
        pushed = True
    return commit_hash, pushed


def run_mobile_sync(
    repository_root: Path,
    *,
    policy: SyncPolicy | None = None,
    task_runner: TaskRunner = execute_task,
) -> SyncResult:
    root = repository_root.resolve()
    active_policy = policy or SyncPolicy()
    git.ensure_repository(root)

    if not active_policy.allow_dirty_worktree:
        git.ensure_clean_worktree(root)

    initial_branch = active_policy.branch or git.current_branch(root)
    git.fetch(remote=active_policy.remote, repository_root=root)
    remote_changed = git.has_remote_changes(
        initial_branch,
        remote=active_policy.remote,
        repository_root=root,
        fetch_first=False,
    )

    pulled = False
    if remote_changed and active_policy.pull:
        git.pull_fast_forward(
            remote=active_policy.remote,
            branch=initial_branch,
            repository_root=root,
        )
        pulled = True

    store = TaskStore(root)
    recovered = store.recover_processing()
    completed: list[str] = []
    failed: list[str] = []
    completed_definitions = []
    commit_hash: str | None = None
    pushed = False

    if active_policy.run_tasks:
        for task in store.list("pending"):
            task_branch = initial_branch
            if active_policy.task_branches:
                task_branch = task.branch or branch_name_for_task(
                    task.task_id, task.task_type
                )
                create_task_branch(
                    task_branch,
                    base_branch=task.base_branch or initial_branch,
                    repository_root=root,
                    remote=active_policy.remote,
                )
            result = task_runner(task, root, store=store)
            write_mobile_summary(root)
            if getattr(result, "status", None) == "completed":
                completed.append(task.task_id)
                completed_definitions.append(task)
                if active_policy.task_branches:
                    commit_hash, pushed_now = _commit_task_if_needed(
                        root, task, active_policy, task_branch
                    )
                    pushed = pushed or pushed_now
            else:
                failed.append(task.task_id)
                break

    if failed:
        write_mobile_summary(root)
        raise SyncError("One or more mobile tasks failed: " + ", ".join(failed))

    if active_policy.task_branches:
        if git.current_branch(root) != initial_branch and not git.changed_files(root):
            checkout_branch(initial_branch, root)
    else:
        task_allows_commit = (
            any(task.execution.auto_save for task in completed_definitions)
            if active_policy.respect_task_policy
            else True
        )
        task_allows_push = (
            any(task.execution.auto_push for task in completed_definitions)
            if active_policy.respect_task_policy
            else True
        )
        if completed and active_policy.auto_commit and task_allows_commit:
            changes = git.changed_files(root)
            if changes:
                git.add(repository_root=root)
                commit_hash = git.commit(
                    active_policy.commit_message, repository_root=root
                )
                if active_policy.auto_push and task_allows_push:
                    git.push(
                        remote=active_policy.remote,
                        branch=initial_branch,
                        repository_root=root,
                    )
                    pushed = True

    write_mobile_summary(root)
    return SyncResult(
        repository_root=root,
        remote_changed=remote_changed,
        pulled=pulled,
        recovered_count=len(recovered),
        completed_tasks=tuple(completed),
        failed_tasks=tuple(failed),
        commit_hash=commit_hash,
        pushed=pushed,
    )
