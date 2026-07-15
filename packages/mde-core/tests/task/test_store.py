from pathlib import Path

from mde.task.loader import load_task
from mde.task.store import TaskStore
from mde.task.types import TaskResult, utc_now


def write_task(root: Path, task_id: str = "TASK-001") -> Path:
    path = root / "tasks" / "pending" / f"{task_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"version: 1\ntask:\n  id: {task_id}\n  type: docs\n  title: Update README\n  workflow: docs\n",
        encoding="utf-8",
    )
    return path


def test_claim_moves_pending_to_processing(tmp_path: Path):
    store = TaskStore(tmp_path)
    task = load_task(write_task(tmp_path))
    claimed = store.claim(task)
    assert claimed.source_path.parent == store.dirs.processing
    assert not (store.dirs.pending / "TASK-001.yaml").exists()


def test_complete_writes_result_yaml(tmp_path: Path):
    store = TaskStore(tmp_path)
    claimed = store.claim(load_task(write_task(tmp_path)))
    now = utc_now()
    result = TaskResult(
        task_id=claimed.task_id,
        status="completed",
        workflow=claimed.workflow,
        started_at=now,
        completed_at=now,
        summary="done",
    )
    result_path = store.complete(claimed, result)
    assert result_path.is_file()
    assert (store.dirs.completed / "TASK-001.yaml").is_file()


def test_recover_processing_moves_tasks_to_failed(tmp_path: Path):
    store = TaskStore(tmp_path)
    claimed = store.claim(load_task(write_task(tmp_path)))
    recovered = store.recover_processing()
    assert len(recovered) == 1
    assert recovered[0].parent == store.dirs.failed
    assert not claimed.source_path.exists()
