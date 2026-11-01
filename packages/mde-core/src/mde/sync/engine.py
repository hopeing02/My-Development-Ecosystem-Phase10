from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable

from mde.git import repository as git
from mde.git.branches import branch_name_for_task, create_task_branch, checkout_branch
from mde.sync.models import SyncPolicy, SyncResult
from mde.task.executor import execute_task
from mde.task.loader import load_task
from mde.task.store import TaskStore
from mde.task.summary import write_mobile_summary
from mde.task.types import TaskDefinition


class SyncError(RuntimeError):
    """Raised when a Mobile Sync cycle cannot complete safely."""


TaskRunner = Callable[..., object]


def _commit_task_if_needed(
    root: Path, task: TaskDefinition, policy: SyncPolicy, branch: str
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


def _validate_batch_plan(
    tasks: list[TaskDefinition], policy: SyncPolicy, initial_branch: str
) -> dict[str, tuple[str, ...]]:
    """Validate opt-in, ordered, shared-branch development batches before execution."""
    positions: dict[str, int] = {}
    for position, task in enumerate(tasks):
        if task.task_id in positions:
            raise SyncError(f"Duplicate pending task ID: {task.task_id}")
        positions[task.task_id] = position

    batches: dict[str, tuple[str, str]] = {}
    branch_owners: dict[str, str] = {}
    dependencies: dict[str, tuple[str, ...]] = {}
    for task in tasks:
        batch_id = task.metadata.get("batch_id")
        declared = task.metadata.get("depends_on", [])
        if batch_id is None and not declared:
            continue  # Unchanged Phase 10 independent-task behavior.
        if not isinstance(batch_id, str) or not batch_id.strip():
            raise SyncError(f"Task {task.task_id}: batch_id is required.")
        if (
            not isinstance(declared, list)
            or any(
                not isinstance(value, str) or not value.strip() for value in declared
            )
            or len(set(declared)) != len(declared)
        ):
            raise SyncError(f"Task {task.task_id}: invalid metadata.depends_on.")
        if not policy.task_branches or not policy.auto_commit:
            raise SyncError(
                "Batched STEP execution requires task branches and commits."
            )
        if not task.branch or task.branch in {
            initial_branch,
            task.base_branch or initial_branch,
        }:
            raise SyncError(
                f"Task {task.task_id}: specify a dedicated repository.branch."
            )
        if not (
            task.execution.auto_apply
            and task.execution.run_tests
            and task.execution.auto_save
        ):
            raise SyncError(
                f"Task {task.task_id}: auto_apply, run_tests "
                "and auto_save must be true."
            )
        branch_spec = (task.branch, task.base_branch or initial_branch)
        if task.branch in branch_owners and branch_owners[task.branch] != batch_id:
            raise SyncError(f"Branch {task.branch}: different batches cannot share it.")
        branch_owners[task.branch] = batch_id
        if batch_id in batches and batches[batch_id] != branch_spec:
            raise SyncError(f"Batch {batch_id}: inconsistent branch or base_branch.")
        batches[batch_id] = branch_spec
        dependencies[task.task_id] = tuple(declared)

        for predecessor_id in declared:
            predecessor_position = positions.get(predecessor_id)
            if predecessor_position is None:
                raise SyncError(
                    f"Task {task.task_id}: predecessor {predecessor_id} is not pending."
                )
            if predecessor_position >= positions[task.task_id]:
                raise SyncError(
                    f"Task {task.task_id}: predecessor {predecessor_id} "
                    "must precede it."
                )
            predecessor = tasks[predecessor_position]
            if (
                predecessor.metadata.get("batch_id") != batch_id
                or predecessor.branch != task.branch
            ):
                raise SyncError(
                    f"Task {task.task_id}: predecessor {predecessor_id} "
                    "must share its batch and branch."
                )
    if batches and len(dependencies) != len(tasks):
        raise SyncError(
            "Batched and independent pending tasks cannot share one G2 run."
        )
    return dependencies


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
    completed_definitions: list[TaskDefinition] = []
    commit_hash: str | None = None
    pushed = False
    dependencies: dict[str, tuple[str, ...]] = {}

    if active_policy.run_tasks:
        pending_tasks = store.list("pending")
        dependencies = _validate_batch_plan(
            pending_tasks, active_policy, initial_branch
        )
        for task in pending_tasks:
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
            if task.task_id in dependencies:
                current = store.find(task.task_id)
                if current is not None and load_task(current[1]) != replace(
                    task, source_path=current[1]
                ):
                    raise SyncError(
                        f"Task {task.task_id}: definition differs on {task_branch}."
                    )
                if current is not None and current[0] == "completed":
                    continue  # Do not repeat a batch task already saved on this branch.
                if current is None or current[0] != "pending":
                    raise SyncError(
                        f"Task {task.task_id}: unexpected state on {task_branch}."
                    )
            for prerequisite in dependencies.get(task.task_id, ()):
                found = store.find(prerequisite)
                if found is None or found[0] != "completed":
                    raise SyncError(
                        f"Task {task.task_id}: predecessor {prerequisite} "
                        "not completed."
                    )
            result = task_runner(task, root, store=store)
            write_mobile_summary(root)
            if getattr(result, "status", None) == "completed":
                if task.task_id in dependencies:
                    saved = store.find(task.task_id)
                    if saved is None or saved[0] != "completed":
                        raise SyncError(
                            f"Task {task.task_id}: completed state was not persisted."
                        )
                completed.append(task.task_id)
                completed_definitions.append(task)
                if active_policy.task_branches:
                    commit_hash, pushed_now = _commit_task_if_needed(
                        root, task, active_policy, task_branch
                    )
                    pushed = pushed or pushed_now
                    if task.task_id in dependencies and commit_hash is None:
                        raise SyncError(
                            f"Task {task.task_id}: no checkpoint commit was produced."
                        )
            else:
                failed.append(task.task_id)
                break

    if failed:
        write_mobile_summary(root)
        raise SyncError("One or more mobile tasks failed: " + ", ".join(failed))

    returned_to_base = False
    if active_policy.task_branches:
        if git.current_branch(root) != initial_branch and not git.changed_files(root):
            checkout_branch(initial_branch, root)
            returned_to_base = True
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

    # Do not dirty the source branch after committing the batch status on its branch.
    if not (dependencies and returned_to_base):
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
