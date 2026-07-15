from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from mde.exceptions import MDEError
from mde.task.types import TaskDefinition, TaskExecutionPolicy


class TaskNotFoundError(MDEError, FileNotFoundError):
    """Raised when a task file cannot be found."""


class TaskValidationError(MDEError, ValueError):
    """Raised when a task YAML document is invalid."""


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TaskValidationError(f"'{name}' must be a mapping.")
    return value


def _require_text(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"Task field '{key}' must be a non-empty string.")
    return value.strip()


def validate_task_document(document: Any) -> TaskDefinition:
    root = _require_mapping(document, "document")
    version = root.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise TaskValidationError("Task 'version' must be a positive integer.")

    task = _require_mapping(root.get("task"), "task")
    repository = task.get("repository") or {}
    execution = task.get("execution") or {}
    inputs = task.get("inputs") or {}
    metadata = task.get("metadata") or {}
    acceptance = task.get("acceptance") or []

    if not isinstance(repository, dict):
        raise TaskValidationError("Task 'repository' must be a mapping.")
    if not isinstance(execution, dict):
        raise TaskValidationError("Task 'execution' must be a mapping.")
    if not isinstance(inputs, dict):
        raise TaskValidationError("Task 'inputs' must be a mapping.")
    if not isinstance(metadata, dict):
        raise TaskValidationError("Task 'metadata' must be a mapping.")
    if not isinstance(acceptance, list) or not all(isinstance(item, str) for item in acceptance):
        raise TaskValidationError("Task 'acceptance' must be a list of strings.")

    return TaskDefinition(
        version=version,
        task_id=_require_text(task, "id"),
        task_type=_require_text(task, "type"),
        title=_require_text(task, "title"),
        description=str(task.get("description", "")).strip(),
        workflow=_require_text(task, "workflow"),
        source=str(task.get("source", "unknown")).strip() or "unknown",
        branch=str(repository["branch"]).strip() if repository.get("branch") else None,
        base_branch=str(repository["base_branch"]).strip() if repository.get("base_branch") else None,
        execution=TaskExecutionPolicy(
            auto_apply=bool(execution.get("auto_apply", False)),
            run_tests=bool(execution.get("run_tests", True)),
            auto_save=bool(execution.get("auto_save", False)),
            auto_push=bool(execution.get("auto_push", False)),
            stop_on_failure=bool(execution.get("stop_on_failure", True)),
        ),
        inputs=dict(inputs),
        acceptance=tuple(item.strip() for item in acceptance if item.strip()),
        metadata=dict(metadata),
    )


def load_task(path: Path) -> TaskDefinition:
    if not path.is_file():
        raise TaskNotFoundError(f"Task file not found: {path}")
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise TaskValidationError(f"Invalid YAML in task '{path}': {error}") from error
    task = validate_task_document(document)
    return TaskDefinition(**{**task.__dict__, "source_path": path.resolve()})
