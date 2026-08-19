"""Orchestrate local ChatGPT export archiving and knowledge projection."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from autoknowledge_lite.chatgpt_archive import (
    ChatGPTArchiveResult,
    ChatGPTArchiveStore,
)
from autoknowledge_lite.chatgpt_knowledge_adapter import (
    ChatGPTKnowledgeAdapter,
    ChatGPTKnowledgeAdapterError,
    ChatGPTKnowledgeProjection,
)
from autoknowledge_lite.chatgpt_session_source import (
    ChatGPTExportSource,
    ChatGPTSessionReference,
    ChatGPTSourceWarning,
)

PROJECTION_SCHEMA_VERSION = "1.0"
CHATGPT_ADAPTER_VERSION = "1.1.0"


class ChatGPTImportError(RuntimeError):
    """Raised when persisted projection state cannot be trusted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ChatGPTProjectionRevision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = PROJECTION_SCHEMA_VERSION
    source_type: Literal["chatgpt"] = "chatgpt"
    adapter_version: str = CHATGPT_ADAPTER_VERSION
    session_id: str = Field(min_length=1)
    revision: int = Field(ge=1)
    import_id: str = Field(min_length=1)
    source_member: str = Field(min_length=1)
    source_index: int = Field(ge=0)
    source_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    projected_at: datetime
    projection: ChatGPTKnowledgeProjection

    @field_validator("projected_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("projected_at must include a timezone")
        return value


class ChatGPTProjectionWriteResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    revision: int
    revision_path: Path
    duplicate: bool
    record: ChatGPTProjectionRevision


class ChatGPTImportIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(min_length=1)
    source_member: str
    source_index: int | None = Field(default=None, ge=0)
    session_id: str | None = None


class ChatGPTImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_id: str
    raw_archive_path: Path
    raw_duplicate: bool
    discovered_sessions: int = Field(ge=0)
    projected_sessions: int = Field(ge=0)
    duplicate_sessions: int = Field(ge=0)
    failed_sessions: int = Field(ge=0)
    issue_report_path: Path | None = None
    revisions: tuple[ChatGPTProjectionWriteResult, ...] = ()
    issues: tuple[ChatGPTImportIssue, ...] = ()


class ChatGPTProjectionStore:
    """Persist immutable per-session projection revisions as local JSON."""

    def __init__(
        self,
        data_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.sessions_dir = self.data_dir / "projections" / "chatgpt" / "sessions"
        self.clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()

    def save(
        self,
        projection: ChatGPTKnowledgeProjection,
        *,
        import_id: str,
        session_ref: ChatGPTSessionReference,
        source_content_hash: str,
    ) -> ChatGPTProjectionWriteResult:
        session_id = projection.session.session_id
        session_dir = self.sessions_dir / self._session_key(session_id)
        with self._lock:
            existing = self._revisions(session_dir)
            if existing:
                latest_path, latest = existing[-1]
                if latest.session_id != session_id:
                    raise ChatGPTImportError(
                        "CHATGPT_PROJECTION_SESSION_KEY_CONFLICT",
                        "Projection session key conflicts with an existing session",
                    )
                if (
                    latest.source_content_hash == source_content_hash
                    and latest.adapter_version == CHATGPT_ADAPTER_VERSION
                ):
                    return ChatGPTProjectionWriteResult(
                        session_id=session_id,
                        revision=latest.revision,
                        revision_path=latest_path,
                        duplicate=True,
                        record=latest,
                    )
                revision = latest.revision + 1
            else:
                revision = 1
            projected_at = self.clock()
            if projected_at.tzinfo is None or projected_at.utcoffset() is None:
                raise ChatGPTImportError(
                    "CHATGPT_PROJECTION_CLOCK_INVALID",
                    "Projection clock must include a timezone",
                )
            record = ChatGPTProjectionRevision(
                session_id=session_id,
                adapter_version=CHATGPT_ADAPTER_VERSION,
                revision=revision,
                import_id=import_id,
                source_member=session_ref.source_member,
                source_index=session_ref.source_index,
                source_content_hash=source_content_hash,
                projected_at=projected_at,
                projection=projection,
            )
            session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination = session_dir / f"revision-{revision:04d}.json"
            temporary = destination.with_suffix(".tmp")
            try:
                temporary.write_text(
                    json.dumps(
                        record.model_dump(mode="json"),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                temporary.chmod(0o600)
                os.replace(temporary, destination)
            except OSError as error:
                temporary.unlink(missing_ok=True)
                raise ChatGPTImportError(
                    "CHATGPT_PROJECTION_WRITE_FAILED",
                    "ChatGPT projection revision could not be persisted",
                ) from error
            return ChatGPTProjectionWriteResult(
                session_id=session_id,
                revision=revision,
                revision_path=destination,
                duplicate=False,
                record=record,
            )

    @staticmethod
    def load(path: Path) -> ChatGPTProjectionRevision:
        try:
            return ChatGPTProjectionRevision.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, ValidationError) as error:
            raise ChatGPTImportError(
                "CHATGPT_PROJECTION_REVISION_INVALID",
                "ChatGPT projection revision is missing or invalid",
            ) from error

    def latest(self, session_id: str) -> ChatGPTProjectionRevision:
        """Return the latest trusted revision for one exact session id."""

        revisions = self._revisions(self.sessions_dir / self._session_key(session_id))
        if not revisions or revisions[-1][1].session_id != session_id:
            raise ChatGPTImportError(
                "CHATGPT_PROJECTION_NOT_FOUND",
                "ChatGPT session projection was not found",
            )
        return revisions[-1][1]

    def latest_revisions(self) -> tuple[ChatGPTProjectionRevision, ...]:
        """Return one latest trusted revision per persisted session."""

        if not self.sessions_dir.exists():
            return ()
        values: list[ChatGPTProjectionRevision] = []
        for session_dir in sorted(self.sessions_dir.glob("session_*")):
            if not session_dir.is_dir():
                continue
            revisions = self._revisions(session_dir)
            if revisions:
                values.append(revisions[-1][1])
        values.sort(key=lambda item: item.projected_at, reverse=True)
        return tuple(values)

    def _revisions(
        self, session_dir: Path
    ) -> list[tuple[Path, ChatGPTProjectionRevision]]:
        if not session_dir.exists():
            return []
        values = [
            (path, self.load(path))
            for path in sorted(session_dir.glob("revision-*.json"))
        ]
        expected = list(range(1, len(values) + 1))
        actual = [record.revision for _, record in values]
        if actual != expected:
            raise ChatGPTImportError(
                "CHATGPT_PROJECTION_REVISION_SEQUENCE_INVALID",
                "ChatGPT projection revision sequence is invalid",
            )
        return values

    @staticmethod
    def _session_key(session_id: str) -> str:
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return f"session_{digest[:24]}"


class ChatGPTIssueReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    import_id: str = Field(min_length=1)
    issues: tuple[ChatGPTImportIssue, ...]


class ChatGPTIssueStore:
    """Persist deterministic import warnings separately from raw source data."""

    def __init__(self, data_dir: Path) -> None:
        self.warnings_dir = data_dir.resolve() / "warnings" / "chatgpt"
        self._lock = Lock()

    def save(
        self, import_id: str, issues: tuple[ChatGPTImportIssue, ...]
    ) -> Path | None:
        if not issues:
            return None
        report = ChatGPTIssueReport(import_id=import_id, issues=issues)
        destination = self.warnings_dir / f"{import_id}.json"
        with self._lock:
            if destination.exists():
                existing = self.load(destination)
                if existing != report:
                    raise ChatGPTImportError(
                        "CHATGPT_IMPORT_ISSUE_REPORT_CONFLICT",
                        "ChatGPT import issue report conflicts with existing data",
                    )
                return destination
            self.warnings_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = destination.with_suffix(".tmp")
            try:
                temporary.write_text(
                    json.dumps(
                        report.model_dump(mode="json"),
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                temporary.chmod(0o600)
                os.replace(temporary, destination)
            except OSError as error:
                temporary.unlink(missing_ok=True)
                raise ChatGPTImportError(
                    "CHATGPT_IMPORT_ISSUE_REPORT_WRITE_FAILED",
                    "ChatGPT import issue report could not be persisted",
                ) from error
        return destination

    @staticmethod
    def load(path: Path) -> ChatGPTIssueReport:
        try:
            return ChatGPTIssueReport.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, ValidationError) as error:
            raise ChatGPTImportError(
                "CHATGPT_IMPORT_ISSUE_REPORT_INVALID",
                "ChatGPT import issue report is missing or invalid",
            ) from error


class ChatGPTImportService:
    """Archive a ChatGPT export, then project each recoverable source Session."""

    def __init__(
        self,
        data_dir: Path,
        *,
        archive_store: ChatGPTArchiveStore | None = None,
        projection_store: ChatGPTProjectionStore | None = None,
        issue_store: ChatGPTIssueStore | None = None,
        adapter: ChatGPTKnowledgeAdapter | None = None,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.archive_store = archive_store or ChatGPTArchiveStore(self.data_dir)
        self.projection_store = projection_store or ChatGPTProjectionStore(
            self.data_dir
        )
        self.issue_store = issue_store or ChatGPTIssueStore(self.data_dir)
        self.adapter = adapter or ChatGPTKnowledgeAdapter()

    def import_export(self, archive_path: Path) -> ChatGPTImportResult:
        source = ChatGPTExportSource(archive_path)
        discovery = source.discover_sessions()
        archived = self.archive_store.archive(discovery)
        archived_source = ChatGPTExportSource(archived.archive_path)
        archived_discovery = archived_source.discover_sessions()
        self._verify_archive(
            discovery.archive_sha256, archived, archived_discovery.archive_sha256
        )

        issues = [
            self._source_issue(warning) for warning in archived_discovery.warnings
        ]
        revisions: list[ChatGPTProjectionWriteResult] = []
        failed_sessions = 0
        for session_ref in archived_discovery.sessions:
            source_session = archived_source.read_session(session_ref)
            source_hash = chatgpt_source_content_hash(source_session)
            try:
                projection = self.adapter.project(source_session)
            except ChatGPTKnowledgeAdapterError as error:
                failed_sessions += 1
                issues.append(
                    ChatGPTImportIssue(
                        code=error.code,
                        source_member=session_ref.source_member,
                        source_index=session_ref.source_index,
                        session_id=session_ref.source_session_id,
                    )
                )
                continue
            revisions.append(
                self.projection_store.save(
                    projection,
                    import_id=archived.import_id,
                    session_ref=session_ref,
                    source_content_hash=source_hash,
                )
            )
            issues.extend(
                ChatGPTImportIssue(
                    code=warning,
                    source_member=session_ref.source_member,
                    source_index=session_ref.source_index,
                    session_id=session_ref.source_session_id,
                )
                for warning in projection.warnings
            )
        duplicate_sessions = sum(item.duplicate for item in revisions)
        issue_report_path = self.issue_store.save(archived.import_id, tuple(issues))
        return ChatGPTImportResult(
            import_id=archived.import_id,
            raw_archive_path=archived.archive_path,
            raw_duplicate=archived.duplicate,
            discovered_sessions=len(archived_discovery.sessions),
            projected_sessions=len(revisions) - duplicate_sessions,
            duplicate_sessions=duplicate_sessions,
            failed_sessions=failed_sessions,
            issue_report_path=issue_report_path,
            revisions=tuple(revisions),
            issues=tuple(issues),
        )

    @staticmethod
    def _verify_archive(
        discovered_hash: str,
        archived: ChatGPTArchiveResult,
        archived_hash: str,
    ) -> None:
        if not (discovered_hash == archived.manifest.archive_sha256 == archived_hash):
            raise ChatGPTImportError(
                "CHATGPT_IMPORT_ARCHIVE_HASH_MISMATCH",
                "Archived ChatGPT export does not match discovery",
            )

    @staticmethod
    def _source_issue(warning: ChatGPTSourceWarning) -> ChatGPTImportIssue:
        return ChatGPTImportIssue(
            code=warning.code,
            source_member=warning.source_member,
            source_index=warning.source_index,
        )


def chatgpt_source_content_hash(source_session: dict[str, object]) -> str:
    """Return the shared canonical source hash used by all ChatGPT imports."""

    canonical = json.dumps(
        source_session,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
