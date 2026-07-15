from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

INBOX_DIR = Path("inbox")
TASKS_DIR = INBOX_DIR / "tasks"
PROCESSING_DIR = INBOX_DIR / "processing"
COMPLETED_DIR = INBOX_DIR / "completed"
FAILED_DIR = INBOX_DIR / "failed"


class QueueError(RuntimeError):
    """Raised when a legacy inbox queue operation cannot be completed."""


@dataclass(frozen=True)
class QueueDirs:
    tasks: Path
    processing: Path
    completed: Path
    failed: Path


def ensure_queue_dirs(root_dir: Path | None = None) -> QueueDirs:
    root = root_dir or Path.cwd()

    dirs = QueueDirs(
        tasks=root / TASKS_DIR,
        processing=root / PROCESSING_DIR,
        completed=root / COMPLETED_DIR,
        failed=root / FAILED_DIR,
    )

    for path in [dirs.tasks, dirs.processing, dirs.completed, dirs.failed]:
        path.mkdir(parents=True, exist_ok=True)

    return dirs


def move_task(task_dir: Path, destination_root: Path) -> Path:
    if not task_dir.is_dir():
        raise QueueError(f"Task directory not found: {task_dir}")

    destination = destination_root / task_dir.name

    if destination.exists():
        raise QueueError(f"Destination already exists: {destination}")

    shutil.move(str(task_dir), str(destination))

    return destination


def move_to_processing(task_dir: Path, root_dir: Path | None = None) -> Path:
    dirs = ensure_queue_dirs(root_dir)
    return move_task(task_dir, dirs.processing)


def move_to_completed(task_dir: Path, root_dir: Path | None = None) -> Path:
    dirs = ensure_queue_dirs(root_dir)
    return move_task(task_dir, dirs.completed)


def move_to_failed(task_dir: Path, root_dir: Path | None = None) -> Path:
    dirs = ensure_queue_dirs(root_dir)
    return move_task(task_dir, dirs.failed)


def recover_processing_tasks(root_dir: Path | None = None) -> list[Path]:
    dirs = ensure_queue_dirs(root_dir)
    recovered: list[Path] = []

    for task_dir in sorted(dirs.processing.iterdir()):
        if not task_dir.is_dir():
            continue

        destination = move_to_failed(
            task_dir,
            root_dir=root_dir,
        )
        recovered.append(destination)

    return recovered
