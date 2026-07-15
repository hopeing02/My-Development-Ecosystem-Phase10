from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

TASKS_DIR = Path("inbox") / "tasks"


class TaskError(RuntimeError):
    """Raised when an MDE task manifest is invalid."""


@dataclass(frozen=True)
class TaskFile:
    patch_path: Path
    target_path: Path


@dataclass(frozen=True)
class TaskManifest:
    task_id: str
    message: str
    manifest_path: Path
    files: list[TaskFile]


def parse_manifest_value(line: str, key: str) -> str:
    prefix = f"{key}:"

    if not line.startswith(prefix):
        raise TaskError(f"Expected manifest key: {key}")

    value = line.removeprefix(prefix).strip()

    if not value:
        raise TaskError(f"Manifest value is empty: {key}")

    return value.strip('"')


def parse_patch_line(line: str) -> str:
    stripped = line.strip()

    if not stripped.startswith("- patch:"):
        raise TaskError("Expected file entry starting with '- patch:'")

    patch_name = stripped.removeprefix("- patch:").strip()

    if not patch_name:
        raise TaskError("Patch file name is empty.")

    return patch_name


def parse_target_line(line: str) -> str:
    stripped = line.strip()

    if not stripped.startswith("target:"):
        raise TaskError("Expected target line.")

    target_name = stripped.removeprefix("target:").strip()

    if not target_name:
        raise TaskError("Target file path is empty.")

    return target_name


def validate_task_files(task_files: list[TaskFile]) -> None:
    if not task_files:
        raise TaskError("Task manifest must contain at least one file.")

    target_paths: set[Path] = set()

    for task_file in task_files:
        if not task_file.patch_path.is_file():
            raise TaskError(f"Patch file not found: {task_file.patch_path}")

        if task_file.target_path.is_absolute():
            raise TaskError(
                f"Absolute target paths are not allowed: {task_file.target_path}"
            )

        if ".." in task_file.target_path.parts:
            raise TaskError(
                f"Parent path traversal is not allowed: {task_file.target_path}"
            )

        if task_file.target_path in target_paths:
            raise TaskError(f"Duplicate target path: {task_file.target_path}")

        target_paths.add(task_file.target_path)


def load_task_manifest(manifest_path: Path) -> TaskManifest:
    if not manifest_path.is_file():
        raise TaskError(f"Manifest file not found: {manifest_path}")

    lines = [
        line.rstrip()
        for line in manifest_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if len(lines) < 5:
        raise TaskError("Manifest is too short.")

    task_id = parse_manifest_value(lines[0], "id")
    message = parse_manifest_value(lines[1], "message")

    if lines[2].strip() != "files:":
        raise TaskError("Expected files section.")

    task_files: list[TaskFile] = []
    index = 3

    while index < len(lines):
        patch_name = parse_patch_line(lines[index])

        if index + 1 >= len(lines):
            raise TaskError(f"Missing target line for patch: {patch_name}")

        target_name = parse_target_line(lines[index + 1])

        task_files.append(
            TaskFile(
                patch_path=manifest_path.parent / patch_name,
                target_path=Path(target_name),
            )
        )

        index += 2

    validate_task_files(task_files)

    return TaskManifest(
        task_id=task_id,
        message=message,
        manifest_path=manifest_path,
        files=task_files,
    )


def ensure_tasks_dir(root_dir: Path | None = None) -> Path:
    root = root_dir or Path.cwd()
    tasks_dir = root / TASKS_DIR
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


def find_task_manifests(root_dir: Path | None = None) -> list[Path]:
    tasks_dir = ensure_tasks_dir(root_dir)

    return sorted(tasks_dir.glob("*/manifest.yaml"))


def load_pending_tasks(root_dir: Path | None = None) -> list[TaskManifest]:
    manifests = find_task_manifests(root_dir)

    return [load_task_manifest(path) for path in manifests]
