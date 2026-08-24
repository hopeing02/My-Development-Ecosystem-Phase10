"""Common structured knowledge contracts for AI development sessions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KnowledgeModel(BaseModel):
    """Strict, immutable base for derived knowledge records."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class SessionSource(StrEnum):
    CHATGPT = "chatgpt"
    CODEX = "codex"
    OTHER = "other"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskBoundaryStatus(StrEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"
    MANUAL = "manual"


class ActivityType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    DECISION = "decision"
    COMMAND = "command"
    FILE_CHANGE = "file_change"
    TEST = "test"
    RESULT = "result"
    NOTE = "note"


class FileChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class TestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class ResultStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class DataSource(StrEnum):
    ORIGINAL = "original"
    DERIVED = "derived"


class DerivationMethod(StrEnum):
    AI = "ai"
    RULE = "rule"
    MANUAL = "manual"


class Provenance(KnowledgeModel):
    """Identifies original facts and separately generated metadata."""

    source: DataSource
    derived_by: DerivationMethod | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_derivation(self) -> Self:
        if self.source == DataSource.DERIVED and self.derived_by is None:
            raise ValueError("derived provenance requires derived_by")
        if self.source == DataSource.ORIGINAL and (
            self.derived_by is not None or self.confidence is not None
        ):
            raise ValueError("original provenance cannot declare derivation metadata")
        return self


class MessageRange(KnowledgeModel):
    start_sequence: int = Field(ge=1)
    end_sequence: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.end_sequence < self.start_sequence:
            raise ValueError("end_sequence must not precede start_sequence")
        return self


class Session(KnowledgeModel):
    session_id: str = Field(min_length=1)
    source: SessionSource
    title: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    source_file: str | None = None
    source_session_id: str | None = None
    capture_id: str | None = None
    document_id: str | None = None
    message_ids: tuple[str, ...] = ()
    task_ids: tuple[str, ...] = ()
    metadata: dict[str, object] = Field(default_factory=dict)
    provenance: Provenance

    @field_validator("created_at", "updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        return _timezone_aware(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")
        return self


class Message(KnowledgeModel):
    message_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    role: MessageRole
    content: str
    timestamp: datetime | None = None
    sequence: int = Field(ge=1)
    source_message_id: str | None = None
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    provenance: Provenance

    @field_validator("timestamp")
    @classmethod
    def require_timestamp_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _timezone_aware(value)


class Task(KnowledgeModel):
    task_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str | None = None
    status: TaskStatus
    boundary_status: TaskBoundaryStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message_range: MessageRange
    activity_ids: tuple[str, ...] = ()
    provenance: Provenance

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_task_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _timezone_aware(value)

    @model_validator(mode="after")
    def validate_completion(self) -> Self:
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at must not precede started_at")
        return self


class Activity(KnowledgeModel):
    activity_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    activity_type: ActivityType
    sequence: int = Field(ge=1)
    timestamp: datetime | None = None
    summary: str | None = None
    entity_refs: tuple[str, ...] = ()
    provenance: Provenance

    @field_validator("timestamp")
    @classmethod
    def require_activity_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _timezone_aware(value)


class Decision(KnowledgeModel):
    decision_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    rationale: str | None = None
    activity_id: str | None = None
    provenance: Provenance


class FileRecord(KnowledgeModel):
    file_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    change_type: FileChangeType
    previous_path: str | None = None
    content_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    added_lines: int | None = Field(default=None, ge=0)
    deleted_lines: int | None = Field(default=None, ge=0)
    provenance: Provenance

    @model_validator(mode="after")
    def validate_rename(self) -> Self:
        if self.change_type == FileChangeType.RENAMED and not self.previous_path:
            raise ValueError("renamed file requires previous_path")
        return self


class CommandRecord(KnowledgeModel):
    command_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    provenance: Provenance

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_command_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _timezone_aware(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at must not precede started_at")
        return self


class TestRecord(KnowledgeModel):
    test_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    status: TestStatus
    output: str | None = None
    command_id: str | None = None
    provenance: Provenance

    @field_validator("started_at", "completed_at")
    @classmethod
    def require_test_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _timezone_aware(value)

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at must not precede started_at")
        return self


class ResultRecord(KnowledgeModel):
    result_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: ResultStatus
    changed_file_ids: tuple[str, ...] = ()
    test_ids: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    provenance: Provenance


def _timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value
