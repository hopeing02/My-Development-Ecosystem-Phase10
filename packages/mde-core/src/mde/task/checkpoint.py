from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import tempfile


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TaskCheckpoint:
    task_id: str
    workflow: str
    status: str
    completed_steps: tuple[str, ...] = ()
    last_successful_step: str | None = None
    updated_at: str = ""
    error: str | None = None


class CheckpointStore:
    def __init__(self, repository_root: Path) -> None:
        self.root = repository_root.resolve() / ".mde" / "checkpoints"
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, task_id: str) -> Path:
        return self.root / f"{task_id}.json"

    def load(self, task_id: str) -> TaskCheckpoint | None:
        path = self.path_for(task_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return TaskCheckpoint(
            task_id=str(data["task_id"]),
            workflow=str(data["workflow"]),
            status=str(data["status"]),
            completed_steps=tuple(data.get("completed_steps", ())),
            last_successful_step=data.get("last_successful_step"),
            updated_at=str(data.get("updated_at", "")),
            error=data.get("error"),
        )

    def write(self, checkpoint: TaskCheckpoint) -> Path:
        path = self.path_for(checkpoint.task_id)
        payload: dict[str, Any] = {
            "task_id": checkpoint.task_id,
            "workflow": checkpoint.workflow,
            "status": checkpoint.status,
            "completed_steps": list(checkpoint.completed_steps),
            "last_successful_step": checkpoint.last_successful_step,
            "updated_at": checkpoint.updated_at or utc_iso(),
            "error": checkpoint.error,
        }
        fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        return path

    def clear(self, task_id: str) -> None:
        self.path_for(task_id).unlink(missing_ok=True)
