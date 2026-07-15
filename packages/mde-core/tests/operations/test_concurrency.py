from pathlib import Path
import pytest

from mde.task.concurrency import TaskExecutionLock, TaskLockError


def test_task_lock_blocks_duplicate_execution(tmp_path: Path) -> None:
    with TaskExecutionLock(tmp_path, "TASK-1"):
        with pytest.raises(TaskLockError):
            with TaskExecutionLock(tmp_path, "TASK-1"):
                pass
    assert not any((tmp_path / ".mde" / "locks").glob("*.lock"))
