from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

from mde.exceptions import MDEError
from mde.task.loader import load_task
from mde.task.types import TaskDefinition, TaskResult


class TaskStoreError(MDEError):
    """Raised when task state cannot be persisted safely."""


@dataclass(frozen=True)
class TaskDirectories:
    pending: Path
    processing: Path
    completed: Path
    failed: Path


class TaskStore:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.root = self.repository_root / "tasks"
        self.dirs = TaskDirectories(
            pending=self.root / "pending",
            processing=self.root / "processing",
            completed=self.root / "completed",
            failed=self.root / "failed",
        )
        for directory in self.dirs.__dict__.values():
            directory.mkdir(parents=True, exist_ok=True)

    def list(self, status: str = "pending") -> list[TaskDefinition]:
        directory = self._status_dir(status)
        return [
            load_task(path)
            for path in sorted(directory.glob("*.yaml"))
            if not path.name.endswith(".result.yaml")
        ]

    def find(self, task_id: str) -> tuple[str, Path] | None:
        for status in ("pending", "processing", "completed", "failed"):
            directory = self._status_dir(status)
            direct = directory / f"{task_id}.yaml"
            if direct.is_file():
                return status, direct
            matches = [
                p
                for p in directory.glob("*.yaml")
                if not p.name.endswith(".result.yaml")
            ]
            for path in matches:
                try:
                    if load_task(path).task_id == task_id:
                        return status, path
                except Exception:
                    continue
        return None

    def claim(self, task: TaskDefinition) -> TaskDefinition:
        if task.source_path is None:
            raise TaskStoreError("Cannot claim a task without source_path.")
        source = task.source_path
        if source.parent.resolve() != self.dirs.pending.resolve():
            raise TaskStoreError(f"Only pending tasks can be claimed: {source}")
        destination = self.dirs.processing / source.name
        if destination.exists():
            raise TaskStoreError(f"Task is already processing: {task.task_id}")
        shutil.move(str(source), str(destination))
        return load_task(destination)

    def complete(self, task: TaskDefinition, result: TaskResult) -> Path:
        return self._finish(task, result, "completed")

    def fail(self, task: TaskDefinition, result: TaskResult) -> Path:
        return self._finish(task, result, "failed")

    def retry(self, task_id: str) -> Path:
        found = self.find(task_id)
        if found is None:
            raise TaskStoreError(f"Task not found: {task_id}")
        status, source = found
        if status != "failed":
            raise TaskStoreError(
                f"Only failed tasks can be retried: {task_id} ({status})"
            )
        destination = self.dirs.pending / source.name
        if destination.exists():
            raise TaskStoreError(f"Pending task already exists: {destination}")
        shutil.move(str(source), str(destination))
        result_path = self.dirs.failed / f"{task_id}.result.yaml"
        result_path.unlink(missing_ok=True)
        return destination

    def recover_processing(self) -> list[Path]:
        recovered: list[Path] = []
        for path in sorted(self.dirs.processing.glob("*.yaml")):
            if path.name.endswith(".result.yaml"):
                continue
            destination = self.dirs.failed / path.name
            if destination.exists():
                raise TaskStoreError(
                    f"Cannot recover task; destination exists: {destination}"
                )
            shutil.move(str(path), str(destination))
            recovered.append(destination)
        return recovered

    def _finish(self, task: TaskDefinition, result: TaskResult, status: str) -> Path:
        if task.source_path is None or not task.source_path.is_file():
            raise TaskStoreError(f"Processing task file not found: {task.source_path}")
        destination_dir = self._status_dir(status)
        destination = destination_dir / task.source_path.name
        if destination.exists():
            raise TaskStoreError(f"Destination already exists: {destination}")
        shutil.move(str(task.source_path), str(destination))
        result_path = destination_dir / f"{task.task_id}.result.yaml"
        payload = {
            "version": 1,
            "result": {
                "task_id": result.task_id,
                "status": result.status,
                "workflow": result.workflow,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat(),
                "steps": list(result.steps),
                "summary": result.summary,
                "error": result.error,
                "last_successful_step": result.last_successful_step,
            },
        }
        result_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return result_path

    def _status_dir(self, status: str) -> Path:
        try:
            return getattr(self.dirs, status)
        except AttributeError as error:
            raise TaskStoreError(f"Unknown task status: {status}") from error
