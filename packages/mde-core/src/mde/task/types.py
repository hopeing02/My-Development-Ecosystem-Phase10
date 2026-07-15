from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

TaskStatus = Literal["pending", "processing", "completed", "failed"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class TaskExecutionPolicy:
    auto_apply: bool = False
    run_tests: bool = True
    auto_save: bool = False
    auto_push: bool = False
    stop_on_failure: bool = True


@dataclass(frozen=True)
class TaskDefinition:
    version: int
    task_id: str
    task_type: str
    title: str
    description: str
    workflow: str
    source: str = "unknown"
    branch: str | None = None
    base_branch: str | None = None
    execution: TaskExecutionPolicy = field(default_factory=TaskExecutionPolicy)
    inputs: dict[str, Any] = field(default_factory=dict)
    acceptance: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: Path | None = None


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    workflow: str
    started_at: datetime
    completed_at: datetime
    steps: tuple[dict[str, Any], ...] = ()
    summary: str = ""
    error: str | None = None
    last_successful_step: str | None = None
    result_path: Path | None = None
