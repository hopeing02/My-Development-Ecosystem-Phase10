from pathlib import Path

from mde.task.executor import execute_task
from mde.task.loader import load_task
from mde.task.store import TaskStore
from mde.workflow.registry import CommandRegistry


def write_task(root: Path, workflow: str = "docs") -> Path:
    path = root / "tasks" / "pending" / "TASK-001.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"version: 1\ntask:\n  id: TASK-001\n  type: docs\n  title: Update README\n  workflow: {workflow}\n",
        encoding="utf-8",
    )
    return path


def test_execute_task_completes_and_persists_result(tmp_path: Path):
    store = TaskStore(tmp_path)
    result = execute_task(load_task(write_task(tmp_path)), tmp_path, store=store)
    assert result.status == "completed"
    assert result.result_path is not None and result.result_path.is_file()
    assert (store.dirs.completed / "TASK-001.yaml").is_file()


def test_execute_task_failure_moves_task_to_failed(tmp_path: Path):
    store = TaskStore(tmp_path)
    registry = CommandRegistry()
    registry.register("task.prepare", lambda context, step: {})
    registry.register("docs.generate", lambda context, step: (_ for _ in ()).throw(RuntimeError("boom")))
    registry.register("change.review", lambda context, step: {})
    registry.register("change.apply", lambda context, step: {})
    registry.register("test.run", lambda context, step: {})
    registry.register("git.save", lambda context, step: {})
    result = execute_task(load_task(write_task(tmp_path)), tmp_path, store=store, registry=registry)
    assert result.status == "failed"
    assert "boom" in (result.error or "")
    assert (store.dirs.failed / "TASK-001.yaml").is_file()


def test_execution_policy_skips_apply_test_save_and_push(tmp_path: Path):
    from mde.task.loader import load_task
    from mde.task.store import TaskStore

    pending = tmp_path / "tasks" / "pending"
    pending.mkdir(parents=True)
    task_path = pending / "TASK-POLICY.yaml"
    task_path.write_text(
        """version: 1
task:
  id: TASK-POLICY
  type: feature
  title: Policy test
  workflow: feature
  execution:
    auto_apply: false
    run_tests: false
    auto_save: false
    auto_push: false
""",
        encoding="utf-8",
    )

    result = execute_task(load_task(task_path), tmp_path, store=TaskStore(tmp_path))
    statuses = {step["command"]: step["status"] for step in result.steps}
    assert statuses["change.apply"] == "skipped"
    assert statuses["test.run"] == "skipped"
    assert statuses["git.save"] == "skipped"
    assert statuses["git.push"] == "skipped"
