"""User-local storage paths for Knowledge Plugin state."""

from __future__ import annotations

import os
from pathlib import Path


def knowledge_data_dir() -> Path:
    """Return the non-project, user-local Knowledge Plugin data directory."""

    configured = os.environ.get("MDE_DATA_HOME", "").strip()
    base = Path(configured).expanduser() if configured else Path.home() / ".mde"
    return base.resolve() / "knowledge"


def source_registry_path() -> Path:
    return knowledge_data_dir() / "sources.json"


def knowledge_database_path() -> Path:
    return knowledge_data_dir() / "knowledge.db"


def knowledge_log_dir() -> Path:
    return knowledge_data_dir() / "logs"
