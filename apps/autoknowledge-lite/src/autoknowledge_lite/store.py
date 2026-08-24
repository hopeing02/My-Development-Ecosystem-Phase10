"""Durable local JSON storage for accepted share jobs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from pydantic import ValidationError

from autoknowledge_lite.models import ShareRecord


class ShareStoreError(RuntimeError):
    """Raised when a share job cannot be persisted safely."""


class ShareNotFoundError(ShareStoreError):
    """Raised when a requested share job does not exist."""


class JsonShareStore:
    """Store each share job as one atomically replaced JSON document."""

    def __init__(self, root: Path | None = None) -> None:
        configured = os.environ.get("AUTOKNOWLEDGE_DATA_DIR")
        if root is not None:
            selected_root = root
        elif configured:
            selected_root = Path(configured)
        else:
            selected_root = _default_data_dir()
        self.root = selected_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save(self, record: ShareRecord) -> Path:
        return self._write(record, require_existing=False)

    def load(self, job_id: str) -> ShareRecord:
        source = self.root / f"{job_id}.json"
        if not source.is_file():
            raise ShareNotFoundError(f"Share job not found: {job_id}")
        try:
            return ShareRecord.model_validate_json(source.read_text(encoding="utf-8"))
        except (OSError, ValidationError, ValueError) as error:
            raise ShareStoreError(
                f"Unable to load share job {job_id}: {error}"
            ) from error

    def update(self, record: ShareRecord) -> Path:
        return self._write(record, require_existing=True)

    def latest_saved(self, *, capture_origin: str) -> ShareRecord | None:
        """Return the latest indexed record for one capture origin."""

        candidates: list[ShareRecord] = []
        for path in self.root.glob("*.json"):
            try:
                record = ShareRecord.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, ValidationError, ValueError):
                continue
            if record.capture_origin == capture_origin and record.document_id:
                candidates.append(record)
        return max(candidates, key=lambda item: item.received_at, default=None)

    def _write(self, record: ShareRecord, *, require_existing: bool) -> Path:
        destination = self.root / f"{record.job_id}.json"
        temporary = destination.with_suffix(".tmp")
        payload = json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        try:
            with self._lock:
                exists = destination.exists()
                if exists and not require_existing:
                    raise ShareStoreError(f"Share job already exists: {record.job_id}")
                if not exists and require_existing:
                    raise ShareNotFoundError(f"Share job not found: {record.job_id}")
                temporary.write_text(payload + "\n", encoding="utf-8")
                temporary.replace(destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise ShareStoreError(
                f"Unable to persist share job {record.job_id}: {error}"
            ) from error
        return destination


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"
