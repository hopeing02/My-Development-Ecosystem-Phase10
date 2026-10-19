from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def templates(self) -> Path:
        return self.root / "templates"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def inbox(self) -> Path:
        return self.root / "inbox"


def discover_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current
