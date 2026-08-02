"""Simple source-local backups for explicit Knowledge Viewer writes."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from mde.knowledge.errors import KnowledgeContractError


class KnowledgeBackupService:
    """Create recoverable backups and retain ten versions per document."""

    def __init__(self, *, retain_per_document: int = 10) -> None:
        self.retain_per_document = retain_per_document

    def create(self, source_root: Path, relative_path: str) -> Path:
        source_file = (source_root / relative_path).resolve(strict=True)
        now = datetime.now().astimezone()
        relative = Path(relative_path)
        destination_dir = source_root / ".mde-backups" / now.strftime("%Y-%m-%d") / relative.parent
        destination = destination_dir / f"{relative.stem}.{now.strftime('%Y%m%d-%H%M%S-%f')}{relative.suffix}"
        try:
            destination_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, destination)
            self._prune(source_root, relative)
        except OSError as error:
            raise KnowledgeContractError("BACKUP_ERROR", "Unable to create document backup.") from error
        return destination

    def _prune(self, source_root: Path, relative: Path) -> None:
        pattern = f"{relative.stem}.*{relative.suffix}"
        candidates = sorted(
            (path for path in (source_root / ".mde-backups").rglob(pattern) if path.parent.parts[-len(relative.parent.parts):] == relative.parent.parts if relative.parent.parts),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ) if relative.parent.parts else sorted(
            (source_root / ".mde-backups").rglob(pattern),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for stale in candidates[self.retain_per_document :]:
            stale.unlink()
