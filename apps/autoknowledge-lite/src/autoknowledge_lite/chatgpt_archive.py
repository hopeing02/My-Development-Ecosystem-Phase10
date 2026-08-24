"""Immutable local archive storage for explicitly imported ChatGPT exports."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from autoknowledge_lite.chatgpt_session_source import ChatGPTSourceDiscovery

MANIFEST_SCHEMA_VERSION = "1.0"
COPY_CHUNK_BYTES = 1024 * 1024


class ChatGPTArchiveError(RuntimeError):
    """Raised when a ChatGPT raw export cannot be archived safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ChatGPTImportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = MANIFEST_SCHEMA_VERSION
    import_id: str = Field(min_length=1)
    source_type: Literal["chatgpt"] = "chatgpt"
    acquisition_method: Literal["export"] = "export"
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    archive_size: int = Field(ge=0)
    original_filename: str = Field(min_length=1)
    imported_at: datetime
    session_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    warning_codes: tuple[str, ...] = ()
    source_members: tuple[str, ...] = ()

    @field_validator("imported_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("imported_at must include a timezone")
        return value


class ChatGPTArchiveResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_id: str
    archive_path: Path
    manifest_path: Path
    duplicate: bool
    manifest: ChatGPTImportManifest


class ChatGPTArchiveStore:
    """Copy raw ChatGPT exports under AUTOKNOWLEDGE_DATA_DIR atomically."""

    def __init__(
        self,
        data_dir: Path | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        configured = os.environ.get("AUTOKNOWLEDGE_DATA_DIR")
        selected = data_dir or (Path(configured) if configured else _default_data_dir())
        self.data_dir = selected.resolve()
        self.imports_dir = self.data_dir / "raw" / "chatgpt" / "imports"
        self.clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()

    def archive(self, discovery: ChatGPTSourceDiscovery) -> ChatGPTArchiveResult:
        source_path = discovery.archive_path.resolve()
        if not source_path.is_file():
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_SOURCE_NOT_FOUND",
                "ChatGPT export source no longer exists",
            )
        current_hash, archive_size = self._hash_file(source_path)
        if current_hash != discovery.archive_sha256:
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_SOURCE_CHANGED",
                "ChatGPT export changed after discovery",
            )
        import_id = f"chatgpt_{current_hash[:24]}"
        destination = self.imports_dir / import_id
        archive_path = destination / "export.zip"
        manifest_path = destination / "manifest.json"

        with self._lock:
            if destination.exists():
                manifest = self._existing_manifest(manifest_path, current_hash)
                return ChatGPTArchiveResult(
                    import_id=import_id,
                    archive_path=archive_path,
                    manifest_path=manifest_path,
                    duplicate=True,
                    manifest=manifest,
                )
            manifest = self._manifest(
                discovery, import_id, archive_size, source_path.name
            )
            self.imports_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            stage = Path(
                tempfile.mkdtemp(prefix=f".{import_id}-", dir=self.imports_dir)
            )
            try:
                staged_archive = stage / "export.zip"
                staged_manifest = stage / "manifest.json"
                copied_hash = self._copy_and_hash(source_path, staged_archive)
                if copied_hash != current_hash:
                    raise ChatGPTArchiveError(
                        "CHATGPT_ARCHIVE_COPY_MISMATCH",
                        "Archived ChatGPT export hash does not match its source",
                    )
                staged_manifest.write_text(
                    json.dumps(
                        manifest.model_dump(mode="json"),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                staged_archive.chmod(0o600)
                staged_manifest.chmod(0o600)
                os.replace(stage, destination)
            except ChatGPTArchiveError:
                self._remove_stage(stage)
                raise
            except OSError as error:
                self._remove_stage(stage)
                raise ChatGPTArchiveError(
                    "CHATGPT_ARCHIVE_WRITE_FAILED",
                    "ChatGPT export archive could not be persisted",
                ) from error
        return ChatGPTArchiveResult(
            import_id=import_id,
            archive_path=archive_path,
            manifest_path=manifest_path,
            duplicate=False,
            manifest=manifest,
        )

    @staticmethod
    def load_manifest(path: Path) -> ChatGPTImportManifest:
        try:
            return ChatGPTImportManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, ValidationError) as error:
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_MANIFEST_INVALID",
                "ChatGPT import manifest is missing or invalid",
            ) from error

    def _existing_manifest(
        self, manifest_path: Path, archive_hash: str
    ) -> ChatGPTImportManifest:
        manifest = self.load_manifest(manifest_path)
        if manifest.archive_sha256 != archive_hash:
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_IMPORT_ID_CONFLICT",
                "ChatGPT import id conflicts with a different archive",
            )
        archive_path = manifest_path.parent / "export.zip"
        existing_hash, existing_size = self._hash_file(archive_path)
        if (
            existing_hash != manifest.archive_sha256
            or existing_size != manifest.archive_size
        ):
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_STORED_COPY_INVALID",
                "Stored ChatGPT export does not match its manifest",
            )
        return manifest

    def _manifest(
        self,
        discovery: ChatGPTSourceDiscovery,
        import_id: str,
        archive_size: int,
        original_filename: str,
    ) -> ChatGPTImportManifest:
        imported_at = self.clock()
        if imported_at.tzinfo is None or imported_at.utcoffset() is None:
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_CLOCK_INVALID",
                "ChatGPT archive clock must include a timezone",
            )
        return ChatGPTImportManifest(
            import_id=import_id,
            archive_sha256=discovery.archive_sha256,
            archive_size=archive_size,
            original_filename=original_filename,
            imported_at=imported_at,
            session_count=len(discovery.sessions),
            warning_count=len(discovery.warnings),
            warning_codes=tuple(
                sorted({warning.code for warning in discovery.warnings})
            ),
            source_members=tuple(
                sorted({session.source_member for session in discovery.sessions})
            ),
        )

    @staticmethod
    def _hash_file(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(COPY_CHUNK_BYTES), b""):
                    digest.update(chunk)
                    size += len(chunk)
        except OSError as error:
            raise ChatGPTArchiveError(
                "CHATGPT_ARCHIVE_SOURCE_UNREADABLE",
                "ChatGPT export source cannot be read",
            ) from error
        return digest.hexdigest(), size

    @staticmethod
    def _copy_and_hash(source_path: Path, destination: Path) -> str:
        digest = hashlib.sha256()
        with source_path.open("rb") as source, destination.open("xb") as target:
            for chunk in iter(lambda: source.read(COPY_CHUNK_BYTES), b""):
                target.write(chunk)
                digest.update(chunk)
            target.flush()
            os.fsync(target.fileno())
        return digest.hexdigest()

    def _remove_stage(self, stage: Path) -> None:
        try:
            resolved = stage.resolve()
            resolved.relative_to(self.imports_dir.resolve())
        except (OSError, ValueError):
            return
        shutil.rmtree(resolved, ignore_errors=True)


def _default_data_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "data"
