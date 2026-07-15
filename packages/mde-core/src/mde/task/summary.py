from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import tempfile

from mde.task.store import TaskStore


def write_mobile_summary(repository_root: Path) -> Path:
    root = repository_root.resolve()
    store = TaskStore(root)
    status_dir = root / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    path = status_dir / "mobile-summary.json"
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            status: len(store.list(status))
            for status in ("pending", "processing", "completed", "failed")
        },
        "latest_completed": [
            {"id": task.task_id, "title": task.title, "workflow": task.workflow}
            for task in store.list("completed")[-10:]
        ],
        "latest_failed": [
            {"id": task.task_id, "title": task.title, "workflow": task.workflow}
            for task in store.list("failed")[-10:]
        ],
    }
    fd, temp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=status_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return path
