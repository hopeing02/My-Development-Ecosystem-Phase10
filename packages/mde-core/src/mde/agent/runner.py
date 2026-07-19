from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from mde.agent.heartbeat import AgentHeartbeat, HeartbeatWriter, utc_iso
from mde.agent.lock import AgentLock, LockError
from mde.logging.logger import build_log_path, close_logger, create_logger
from mde.sync.engine import SyncError, run_mobile_sync
from mde.sync.models import SyncPolicy


class AgentError(RuntimeError):
    """Raised when an MDE agent cycle fails."""


@dataclass(frozen=True)
class AgentResult:
    remote_changed: bool
    pulled: bool
    recovered_count: int
    completed_tasks: tuple[str, ...]
    failed_tasks: tuple[str, ...]
    commit_hash: str | None
    pushed: bool
    heartbeat_path: Path
    log_path: Path
    elapsed_seconds: float


def run_once(
    auto_save: bool = False,
    *,
    repository_root: Path | None = None,
    auto_push: bool | None = None,
    allow_dirty_worktree: bool = False,
    remote: str = "origin",
    branch: str | None = None,
) -> AgentResult:
    """Run one self-healing Mobile Sync cycle under the Agent lock.

    Task workflows execute Ruff auto-fix, Ruff validation, pytest, and the bounded
    AI repair loop before Mobile Sync commits or pushes any result. ``save`` remains
    a separate final Git-only command for manual use.
    """
    root = (repository_root or Path.cwd()).resolve()
    started_perf = time.perf_counter()
    started_at = utc_iso()
    log_path = build_log_path("agent", root)
    logger = create_logger("mde.agent", log_path)
    heartbeat = HeartbeatWriter(root)
    push_enabled = True if auto_push is None else auto_push
    commit_enabled = True

    heartbeat.write(
        AgentHeartbeat(status="running", started_at=started_at, updated_at=started_at)
    )

    try:
        with AgentLock(root):
            logger.info("MDE Agent self-healing Mobile Sync cycle started: %s", root)
            sync_result = run_mobile_sync(
                root,
                policy=SyncPolicy(
                    remote=remote,
                    branch=branch,
                    auto_commit=commit_enabled,
                    auto_push=push_enabled and commit_enabled,
                    allow_dirty_worktree=allow_dirty_worktree,
                    respect_task_policy=True,
                    task_branches=True,
                ),
            )
            completed_at = utc_iso()
            heartbeat_path = heartbeat.write(
                AgentHeartbeat(
                    status="completed",
                    started_at=started_at,
                    updated_at=completed_at,
                    completed_at=completed_at,
                    remote_changed=sync_result.remote_changed,
                    completed_tasks=sync_result.completed_tasks,
                    failed_tasks=sync_result.failed_tasks,
                    commit_hash=sync_result.commit_hash,
                    pushed=sync_result.pushed,
                )
            )
            result = AgentResult(
                remote_changed=sync_result.remote_changed,
                pulled=sync_result.pulled,
                recovered_count=sync_result.recovered_count,
                completed_tasks=sync_result.completed_tasks,
                failed_tasks=sync_result.failed_tasks,
                commit_hash=sync_result.commit_hash,
                pushed=sync_result.pushed,
                heartbeat_path=heartbeat_path,
                log_path=log_path,
                elapsed_seconds=time.perf_counter() - started_perf,
            )
            logger.info(
                "Agent completed: recovered=%d completed=%d failed=%d commit=%s pushed=%s",
                result.recovered_count,
                len(result.completed_tasks),
                len(result.failed_tasks),
                result.commit_hash,
                result.pushed,
            )
            _print_result(result)
            return result
    except (SyncError, LockError, RuntimeError) as error:
        failed_at = utc_iso()
        heartbeat.write(
            AgentHeartbeat(
                status="failed",
                started_at=started_at,
                updated_at=failed_at,
                completed_at=failed_at,
                error=str(error),
            )
        )
        logger.exception("MDE Agent cycle failed.")
        raise AgentError(str(error)) from error
    finally:
        close_logger(logger)


def run_watch(
    interval_seconds: int = 30,
    auto_save: bool = False,
    max_cycles: int | None = None,
    *,
    repository_root: Path | None = None,
    auto_push: bool | None = None,
) -> None:
    if interval_seconds < 5:
        raise AgentError("Watch interval must be at least 5 seconds.")
    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"Agent watch cycle: {cycle}")
            try:
                run_once(
                    auto_save=auto_save,
                    repository_root=repository_root,
                    auto_push=auto_push,
                )
            except AgentError as error:
                print(f"Agent cycle failed: {error}")
            if max_cycles is not None and cycle >= max_cycles:
                return
            print(f"Next check in {interval_seconds} seconds...")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("MDE agent watch stopped.")


def _print_result(result: AgentResult) -> None:
    print("================================")
    print("MDE Agent result")
    print("--------------------------------")
    print(f"Remote changed : {result.remote_changed}")
    print(f"Pulled         : {result.pulled}")
    print(f"Recovered      : {result.recovered_count}")
    print(f"Completed      : {len(result.completed_tasks)}")
    print(f"Failed         : {len(result.failed_tasks)}")
    print(f"Commit         : {result.commit_hash or '-'}")
    print(f"Pushed         : {result.pushed}")
    print(f"Heartbeat      : {result.heartbeat_path}")
    print(f"Log            : {result.log_path}")
    print(f"Elapsed        : {result.elapsed_seconds:.2f} seconds")
    print("================================")
