from pathlib import Path

from mde.task.store import TaskStore

TASK = """version: 1
task:
  id: TASK-RETRY
  type: bugfix
  title: retry
  workflow: bugfix
"""


def test_failed_task_can_return_to_pending(tmp_path: Path) -> None:
    store = TaskStore(tmp_path)
    failed = store.dirs.failed / "TASK-RETRY.yaml"
    failed.write_text(TASK, encoding="utf-8")
    (store.dirs.failed / "TASK-RETRY.result.yaml").write_text(
        "result: {}", encoding="utf-8"
    )
    destination = store.retry("TASK-RETRY")
    assert destination.parent == store.dirs.pending
    assert destination.exists()
    assert not (store.dirs.failed / "TASK-RETRY.result.yaml").exists()
