from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentHeartbeat:
    status: str
    started_at: str
    updated_at: str
    completed_at: str | None = None
    remote_changed: bool = False
    completed_tasks: tuple[str, ...] = ()
    failed_tasks: tuple[str, ...] = ()
    commit_hash: str | None = None
    pushed: bool = False
    error: str | None = None


class HeartbeatWriter:
    def __init__(self, repository_root: Path) -> None:
        self.path = repository_root.resolve() / "status" / "agent-heartbeat.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, heartbeat: AgentHeartbeat) -> Path:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(heartbeat), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
        return self.path
