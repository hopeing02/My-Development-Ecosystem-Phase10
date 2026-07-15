from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    command: str
    args: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()
    enabled: bool = True
    continue_on_error: bool = False
    timeout: int | None = None
    retry: int = 0
    condition: str | None = None


@dataclass(frozen=True)
class WorkflowDefinition:
    version: int
    name: str
    description: str
    steps: tuple[WorkflowStep, ...]
    source_path: Path | None = None


@dataclass
class WorkflowContext:
    workflow_name: str
    message: str = ""
    repository_root: Path = field(default_factory=Path.cwd)
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StepResult:
    step_id: str
    command: str
    status: StepStatus
    started_at: datetime
    completed_at: datetime
    message: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    attempts: int = 1


@dataclass(frozen=True)
class WorkflowResult:
    workflow_name: str
    status: Literal["completed", "failed"]
    started_at: datetime
    completed_at: datetime
    steps: tuple[StepResult, ...]
    error: str | None = None
