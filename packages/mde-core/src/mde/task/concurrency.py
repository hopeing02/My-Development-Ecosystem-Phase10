from __future__ import annotations

import os
from pathlib import Path


class TaskLockError(RuntimeError):
    """Raised when a task execution lock cannot be acquired or released."""


class TaskExecutionLock:
    def __init__(self, repository_root: Path, task_id: str) -> None:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in task_id)
        self.path = repository_root.resolve() / ".mde" / "locks" / f"task-{safe}.lock"
        self.fd: int | None = None

    def __enter__(self) -> "TaskExecutionLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(self.fd, str(os.getpid()).encode("ascii"))
        except FileExistsError as error:
            raise TaskLockError(f"Task is already locked: {self.path.stem}") from error
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.path.unlink(missing_ok=True)
