from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from mde.sync.engine import SyncError, run_mobile_sync
from mde.sync.models import SyncPolicy


def patch_git(monkeypatch, *, changed=False, files=()):
    calls = []
    monkeypatch.setattr("mde.sync.engine.git.ensure_repository", lambda root: root)
    monkeypatch.setattr(
        "mde.sync.engine.git.ensure_clean_worktree", lambda root: calls.append("clean")
    )
    monkeypatch.setattr(
        "mde.sync.engine.git.current_branch", lambda root: "feature/mobile-sync"
    )
    monkeypatch.setattr(
        "mde.sync.engine.git.fetch", lambda **kwargs: calls.append("fetch")
    )
    monkeypatch.setattr(
        "mde.sync.engine.git.has_remote_changes", lambda *args, **kwargs: changed
    )
    monkeypatch.setattr(
        "mde.sync.engine.git.pull_fast_forward", lambda **kwargs: calls.append("pull")
    )
    monkeypatch.setattr("mde.sync.engine.git.changed_files", lambda root: tuple(files))
    monkeypatch.setattr("mde.sync.engine.git.add", lambda **kwargs: calls.append("add"))
    monkeypatch.setattr(
        "mde.sync.engine.git.commit",
        lambda *args, **kwargs: calls.append("commit") or "abc123",
    )
    monkeypatch.setattr(
        "mde.sync.engine.git.push", lambda **kwargs: calls.append("push")
    )
    return calls


def test_sync_fetches_and_pulls_remote_changes(tmp_path: Path, monkeypatch):
    calls = patch_git(monkeypatch, changed=True)
    result = run_mobile_sync(tmp_path, policy=SyncPolicy(run_tasks=False))
    assert result.remote_changed is True
    assert result.pulled is True
    assert calls[:3] == ["clean", "fetch", "pull"]


def test_sync_does_not_pull_when_remote_is_equal(tmp_path: Path, monkeypatch):
    calls = patch_git(monkeypatch, changed=False)
    result = run_mobile_sync(tmp_path, policy=SyncPolicy(run_tasks=False))
    assert result.pulled is False
    assert "pull" not in calls


def test_sync_executes_pending_task_and_pushes_result(tmp_path: Path, monkeypatch):
    calls = patch_git(monkeypatch, files=("M tasks/completed/TASK-1.yaml",))
    pending = tmp_path / "tasks" / "pending"
    pending.mkdir(parents=True)
    (pending / "TASK-1.yaml").write_text(
        """version: 1\ntask:\n  id: TASK-1\n  type: docs\n  title: Update docs\n  workflow: docs\n""",
        encoding="utf-8",
    )

    def runner(task, root, store):
        active = store.claim(task)
        result = SimpleNamespace(status="completed")
        from mde.task.types import TaskResult, utc_now

        finished = TaskResult(
            task_id=active.task_id,
            status="completed",
            workflow=active.workflow,
            started_at=utc_now(),
            completed_at=utc_now(),
        )
        store.complete(active, finished)
        return result

    result = run_mobile_sync(tmp_path, task_runner=runner)
    assert result.completed_tasks == ("TASK-1",)
    assert result.commit_hash == "abc123"
    assert result.pushed is True
    assert calls[-3:] == ["add", "commit", "push"]


def test_sync_skips_commit_when_no_files_changed(tmp_path: Path, monkeypatch):
    calls = patch_git(monkeypatch, files=())
    result = run_mobile_sync(tmp_path, policy=SyncPolicy(run_tasks=False))
    assert result.commit_hash is None
    assert "commit" not in calls


def test_sync_stops_when_task_fails(tmp_path: Path, monkeypatch):
    patch_git(monkeypatch)
    pending = tmp_path / "tasks" / "pending"
    pending.mkdir(parents=True)
    (pending / "TASK-X.yaml").write_text(
        """version: 1\ntask:\n  id: TASK-X\n  type: docs\n  title: Broken\n  workflow: docs\n""",
        encoding="utf-8",
    )

    def runner(task, root, store):
        return SimpleNamespace(status="failed")

    with pytest.raises(SyncError, match="TASK-X"):
        run_mobile_sync(tmp_path, task_runner=runner)


def test_sync_respects_task_save_policy(tmp_path: Path, monkeypatch):
    calls = patch_git(monkeypatch, files=("tasks/completed/TASK-NO-SAVE.yaml",))
    pending = tmp_path / "tasks" / "pending"
    pending.mkdir(parents=True)
    (pending / "TASK-NO-SAVE.yaml").write_text(
        """version: 1
task:
  id: TASK-NO-SAVE
  type: docs
  title: No save
  workflow: docs
  execution:
    auto_save: false
    auto_push: false
""",
        encoding="utf-8",
    )

    def runner(task, root, store):
        active = store.claim(task)
        from mde.task.types import TaskResult, utc_now

        finished = TaskResult(
            task_id=active.task_id,
            status="completed",
            workflow=active.workflow,
            started_at=utc_now(),
            completed_at=utc_now(),
        )
        store.complete(active, finished)
        return finished

    result = run_mobile_sync(
        tmp_path,
        policy=SyncPolicy(respect_task_policy=True),
        task_runner=runner,
    )
    assert result.commit_hash is None
    assert "commit" not in calls
