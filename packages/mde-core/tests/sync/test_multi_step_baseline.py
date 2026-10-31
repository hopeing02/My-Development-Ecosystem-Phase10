from pathlib import Path

import pytest

from mde.sync.engine import SyncError, run_mobile_sync
from mde.sync.models import SyncPolicy
from mde.task.store import TaskStore
from mde.task.types import TaskResult, utc_now


def _write_pending_task(root: Path, filename: str, task_id: str) -> None:
    pending = root / "tasks" / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    (pending / filename).write_text(
        "version: 1\n"
        "task:\n"
        f"  id: {task_id}\n"
        "  type: docs\n"
        f"  title: {task_id}\n"
        "  workflow: docs\n",
        encoding="utf-8",
    )


def _mock_git_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mde.sync.engine.git.ensure_repository", lambda root: None)
    monkeypatch.setattr("mde.sync.engine.git.ensure_clean_worktree", lambda root: None)
    monkeypatch.setattr("mde.sync.engine.git.current_branch", lambda root: "main")
    monkeypatch.setattr("mde.sync.engine.git.fetch", lambda **kwargs: None)
    monkeypatch.setattr(
        "mde.sync.engine.git.has_remote_changes", lambda *args, **kwargs: False
    )


def test_multiple_pending_tasks_run_in_filename_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_git_without_network(monkeypatch)
    _write_pending_task(tmp_path, "02-second.yaml", "STEP-002")
    _write_pending_task(tmp_path, "01-first.yaml", "STEP-001")
    visited: list[str] = []

    def runner(task, root, *, store):
        visited.append(task.task_id)
        active = store.claim(task)
        now = utc_now()
        result = TaskResult(
            task_id=active.task_id,
            status="completed",
            workflow=active.workflow,
            started_at=now,
            completed_at=now,
        )
        store.complete(active, result)
        return result

    result = run_mobile_sync(
        tmp_path,
        policy=SyncPolicy(auto_commit=False, auto_push=False, task_branches=False),
        task_runner=runner,
    )

    assert visited == ["STEP-001", "STEP-002"]
    assert result.completed_tasks == ("STEP-001", "STEP-002")
    store = TaskStore(tmp_path)
    assert store.find("STEP-001")[0] == "completed"
    assert store.find("STEP-002")[0] == "completed"


def test_failed_step_stops_later_pending_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_git_without_network(monkeypatch)
    _write_pending_task(tmp_path, "01-first.yaml", "STEP-001")
    _write_pending_task(tmp_path, "02-failing.yaml", "STEP-002")
    _write_pending_task(tmp_path, "03-not-run.yaml", "STEP-003")
    visited: list[str] = []

    def runner(task, root, *, store):
        visited.append(task.task_id)
        active = store.claim(task)
        now = utc_now()
        status = "failed" if active.task_id == "STEP-002" else "completed"
        result = TaskResult(
            task_id=active.task_id,
            status=status,
            workflow=active.workflow,
            started_at=now,
            completed_at=now,
        )
        if status == "failed":
            store.fail(active, result)
        else:
            store.complete(active, result)
        return result

    with pytest.raises(SyncError, match="STEP-002"):
        run_mobile_sync(
            tmp_path,
            policy=SyncPolicy(auto_commit=False, auto_push=False, task_branches=False),
            task_runner=runner,
        )

    assert visited == ["STEP-001", "STEP-002"]
    store = TaskStore(tmp_path)
    assert store.find("STEP-001")[0] == "completed"
    assert store.find("STEP-002")[0] == "failed"
    assert store.find("STEP-003")[0] == "pending"
