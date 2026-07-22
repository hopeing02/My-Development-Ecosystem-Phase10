"""Privacy-safe, user-local audit logging for Knowledge Plugin operations."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock

from mde.knowledge.models import KnowledgeSource, ScanResult, utc_now

DEFAULT_AUDIT_RETENTION_DAYS = 30
_AUDIT_FILE_NAME = re.compile(r"knowledge-(\d{4}-\d{2}-\d{2})\.log\Z")


class KnowledgeAuditLogger:
    """Append structured audit events without document or query content."""

    def __init__(
        self,
        directory: Path,
        *,
        clock: Callable[[], datetime] = utc_now,
        retention_days: int = DEFAULT_AUDIT_RETENTION_DAYS,
    ) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be at least 1.")
        self.directory = directory
        self._clock = clock
        self.retention_days = retention_days
        self._lock = Lock()

    def prune(self, reference_date: date | None = None) -> tuple[Path, ...]:
        """Delete only expired, regular Knowledge audit log files."""

        if not self.directory.exists():
            return ()
        today = reference_date or self._clock().date()
        cutoff = today - timedelta(days=self.retention_days)
        root = self.directory.resolve()
        removed: list[Path] = []
        for candidate in self.directory.glob("knowledge-*.log"):
            match = _AUDIT_FILE_NAME.fullmatch(candidate.name)
            if match is None or candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                log_date = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            if log_date > cutoff or candidate.resolve().parent != root:
                continue
            candidate.unlink()
            removed.append(candidate)
        return tuple(sorted(removed))

    def source_added(self, source: KnowledgeSource) -> Path:
        return self._write("source.added", source)

    def source_updated(
        self, source: KnowledgeSource, changes: Mapping[str, bool]
    ) -> Path:
        return self._write("source.updated", source, changes=dict(changes))

    def source_removed(self, source: KnowledgeSource) -> Path:
        return self._write("source.removed", source)

    def scan_started(self, source: KnowledgeSource) -> Path:
        return self._write("scan.started", source)

    def scan_completed(self, result: ScanResult) -> Path:
        return self._write(
            "scan.completed",
            result.source,
            counts={
                "added": result.added_count,
                "updated": result.updated_count,
                "deleted": result.deleted_count,
                "unchanged": result.unchanged_count,
                "errors": result.error_count,
            },
            file_errors=[
                {"relative_path": error.relative_path, "error": error.message}
                for error in result.errors
            ],
        )

    def scan_failed(self, source: KnowledgeSource, error: BaseException) -> Path:
        return self._write(
            "scan.failed",
            source,
            error_type=type(error).__name__,
        )

    def _write(
        self,
        event: str,
        source: KnowledgeSource,
        **details: object,
    ) -> Path:
        timestamp = self._clock()
        payload: dict[str, object] = {
            "timestamp": timestamp.isoformat(),
            "event": event,
            "source_id": source.id,
            "source_name": source.name,
            "category": source.category,
            "sensitive": source.sensitive,
            **details,
        }
        self.directory.mkdir(parents=True, exist_ok=True)
        self.prune(timestamp.date())
        path = self.directory / f"knowledge-{timestamp.date().isoformat()}.log"
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock, path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
        return path
