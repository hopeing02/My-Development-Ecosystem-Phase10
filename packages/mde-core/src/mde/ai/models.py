from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

AIAction = Literal["generate", "review", "fix", "summarize"]


@dataclass(frozen=True)
class AIArtifact:
    path: str
    content: str
    media_type: str = "text/plain"


@dataclass(frozen=True)
class AIRequest:
    action: AIAction
    prompt: str
    repository_root: Path
    task_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    provider: str
    action: AIAction
    summary: str
    artifacts: tuple[AIArtifact, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
