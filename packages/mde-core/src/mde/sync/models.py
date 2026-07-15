from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SyncPolicy:
    remote: str = "origin"
    branch: str | None = None
    pull: bool = True
    run_tasks: bool = True
    auto_commit: bool = True
    auto_push: bool = True
    allow_dirty_worktree: bool = False
    commit_message: str = "chore(sync): process mobile tasks"
    respect_task_policy: bool = False
    task_branches: bool = False


@dataclass(frozen=True)
class SyncResult:
    repository_root: Path
    remote_changed: bool
    pulled: bool
    recovered_count: int
    completed_tasks: tuple[str, ...]
    failed_tasks: tuple[str, ...]
    commit_hash: str | None = None
    pushed: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.failed_tasks
