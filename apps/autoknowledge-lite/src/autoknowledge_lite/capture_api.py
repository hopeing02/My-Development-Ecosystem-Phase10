"""Versioned capture contract and persistence pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from autoknowledge_lite.models import ALLOWED_VAULT_FOLDERS

SCHEMA_VERSION = "1.0"
MAX_CLIPBOARD_BYTES = 1024 * 1024
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|ghp|gho|github_pat)-?[A-Za-z0-9_\-]{16,}\b"),
    re.compile(r"(?i)authorization\s*:\s*bearer\s+\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|oauth[_-]?token|"
        r"access[_-]?token)\s*[:=]\s*[^\s]{6,}"
    ),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?<!\d)\d{6}-?[1-4]\d{6}(?!\d)"),
    re.compile(r"(?<!\d)(?:\d[ -]?){15}\d(?!\d)"),
)


class CaptureType(StrEnum):
    CLIPBOARD_ITEM = "clipboard_item"
    DEVELOPMENT_SESSION = "development_session"


class SourceType(StrEnum):
    CHATGPT = "chatgpt"
    CODEX = "codex"
    GENERAL = "general"


class CaptureDevice(StrEnum):
    ANDROID = "android"
    WINDOWS = "windows"


class RelationType(StrEnum):
    EXCERPT_OF = "excerpt_of"
    BELONGS_TO_PROJECT = "belongs_to_project"
    PARENT_OF = "parent_of"
    REFERENCES = "references"
    CHANGED_FILE = "changed_file"
    TESTED_BY = "tested_by"
    SUPERSEDES = "supersedes"


class ClipboardItemPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    title: str | None = Field(default=None, max_length=200)
    mime_type: str = Field(default="text/plain", alias="mimeType", max_length=100)
    language: str | None = Field(default=None, max_length=50)


class DevelopmentRepository(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    root_alias: str = Field(alias="rootAlias", min_length=1, max_length=500)
    branch: str | None = Field(default=None, max_length=300)
    branch_before: str | None = Field(
        default=None, alias="branchBefore", max_length=300
    )
    branch_after: str | None = Field(default=None, alias="branchAfter", max_length=300)
    head_before: str | None = Field(default=None, alias="headBefore", max_length=100)
    head_after: str | None = Field(default=None, alias="headAfter", max_length=100)
    worktree_path_alias: str | None = Field(
        default=None, alias="worktreePathAlias", max_length=500
    )


class DevelopmentSessionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capture_session_id: str | None = Field(
        default=None, alias="captureSessionId", min_length=1, max_length=500
    )
    source_session_id: str | None = Field(
        default=None, alias="sourceSessionId", min_length=1, max_length=500
    )
    client_type: str = Field(alias="clientType", min_length=1, max_length=100)
    title: str = Field(
        default="Codex development session", min_length=1, max_length=200
    )
    request: str | None = Field(default=None, max_length=10000)
    wrapper_request: str | None = Field(
        default=None, alias="wrapperRequest", max_length=10000
    )
    first_codex_user_message: str | None = Field(
        default=None, alias="firstCodexUserMessage", max_length=300000
    )
    summary: str | None = Field(default=None, max_length=10000)
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime | None = Field(default=None, alias="endedAt")
    closure_reason: str | None = Field(
        default=None, alias="closureReason", max_length=100
    )
    repository: DevelopmentRepository | None = None
    before_snapshot: dict[str, Any] = Field(
        default_factory=dict, alias="beforeSnapshot"
    )
    after_snapshot: dict[str, Any] = Field(default_factory=dict, alias="afterSnapshot")
    messages: list[dict[str, Any]] = Field(default_factory=list)
    session_link_confidence: str | None = Field(
        default=None, alias="sessionLinkConfidence", max_length=20
    )
    session_link_reason: str | None = Field(
        default=None, alias="sessionLinkReason", max_length=200
    )
    adapter: dict[str, Any] | None = None
    notes: list[dict[str, Any]] = Field(default_factory=list)
    commands: list[dict[str, Any]] = Field(default_factory=list)
    changed_files: list[dict[str, Any]] = Field(
        default_factory=list, alias="changedFiles"
    )
    tests: list[dict[str, Any]] = Field(default_factory=list)
    attachments: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_time_range(self) -> DevelopmentSessionPayload:
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("startedAt must include a timezone")
        if self.ended_at is not None:
            if self.ended_at.tzinfo is None or self.ended_at.utcoffset() is None:
                raise ValueError("endedAt must include a timezone")
            if self.ended_at < self.started_at:
                raise ValueError("endedAt must not precede startedAt")
        return self


class CaptureEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_version: str = Field(alias="schemaVersion")
    capture_id: str = Field(alias="captureId", min_length=1, max_length=200)
    source_type: SourceType = Field(alias="sourceType")
    capture_type: CaptureType = Field(alias="captureType")
    capture_device: CaptureDevice = Field(alias="captureDevice")
    capture_method: str = Field(alias="captureMethod", min_length=1, max_length=100)
    project_id: str | None = Field(default=None, alias="projectId", max_length=200)
    target_folder: str = Field(alias="targetFolder", min_length=1, max_length=200)
    parent_document: str | None = Field(
        default=None, alias="parentDocument", max_length=2000
    )
    captured_at: datetime = Field(alias="capturedAt")
    device_id: str = Field(alias="deviceId", min_length=1, max_length=200)
    content_hash: str = Field(alias="contentHash")
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any]

    @field_validator("schema_version")
    @classmethod
    def supported_schema(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError("unsupported schema version")
        return value

    @field_validator("captured_at")
    @classmethod
    def captured_at_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("capturedAt must include a timezone")
        return value

    @field_validator("content_hash")
    @classmethod
    def valid_content_hash(cls, value: str) -> str:
        normalized = value.lower()
        if not SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("contentHash must be a lowercase SHA-256 value")
        return normalized

    @model_validator(mode="after")
    def validate_typed_payload(self) -> CaptureEnvelope:
        if self.capture_type == CaptureType.CLIPBOARD_ITEM:
            ClipboardItemPayload.model_validate(self.payload)
        else:
            DevelopmentSessionPayload.model_validate(self.payload)
        return self


class CaptureRelation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    relation_type: RelationType = Field(alias="relationType")
    from_capture_id: str = Field(alias="fromCaptureId")
    to_entity_type: str = Field(alias="toEntityType")
    to_entity_id: str = Field(alias="toEntityId")


class CaptureResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    capture_id: str = Field(alias="captureId")
    document_id: str | None = Field(alias="documentId")
    document_path: str | None = Field(alias="documentPath")
    capture_type: CaptureType = Field(alias="captureType")
    duplicate: bool
    revision: int = 1
    warnings: list[str] = Field(default_factory=list)


class CaptureErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class CaptureErrorResponse(BaseModel):
    status: str = "error"
    error: CaptureErrorDetail
    warnings: list[str] = Field(default_factory=list)


class CaptureError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        http_status: int = status.HTTP_422_UNPROCESSABLE_ENTITY,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.http_status = http_status

    def response(self) -> CaptureErrorResponse:
        return CaptureErrorResponse(
            error=CaptureErrorDetail(
                code=self.code,
                message=self.message,
                field=self.field,
            )
        )


class CaptureHandler(Protocol):
    def supports(self, capture_type: CaptureType) -> bool: ...

    def handle(self, envelope: CaptureEnvelope) -> CaptureResult: ...


class CaptureHandlerRegistry:
    def __init__(self, handlers: tuple[CaptureHandler, ...]) -> None:
        self._handlers = handlers

    def resolve(self, capture_type: CaptureType) -> CaptureHandler:
        for handler in self._handlers:
            if handler.supports(capture_type):
                return handler
        raise CaptureError(
            "INVALID_CAPTURE_TYPE",
            "지원하지 않는 captureType입니다.",
            field="captureType",
        )


class KnowledgeIndexer(Protocol):
    def index_file(self, source: str, relative_path: str) -> dict[str, Any]: ...

    def link_child(
        self, source: str, parent_document_id: str, target_document_id: str
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class CaptureIndexEntry:
    capture_id: str
    capture_type: str
    server_content_hash: str
    document_id: str
    document_path: str
    created_at: str
    request_fingerprint: str
    response: dict[str, Any]


class CaptureIndexStore:
    """Atomically persist capture idempotency and content-deduplication metadata."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._lock = Lock()

    def find_capture(self, capture_id: str) -> CaptureIndexEntry | None:
        with self._lock:
            return self._entries().get(capture_id)

    def find_hash(self, content_hash: str) -> CaptureIndexEntry | None:
        with self._lock:
            return next(
                (
                    item
                    for item in self._entries().values()
                    if item.server_content_hash == content_hash
                ),
                None,
            )

    def add(self, entry: CaptureIndexEntry) -> None:
        with self._lock:
            entries = self._entries()
            entries[entry.capture_id] = entry
            payload = {
                capture_id: {
                    "captureId": item.capture_id,
                    "captureType": item.capture_type,
                    "serverContentHash": item.server_content_hash,
                    "documentId": item.document_id,
                    "documentPath": item.document_path,
                    "createdAt": item.created_at,
                    "requestFingerprint": item.request_fingerprint,
                    "response": item.response,
                }
                for capture_id, item in entries.items()
            }
            temporary = self.path.with_suffix(".tmp")
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temporary.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                os.replace(temporary, self.path)
            except OSError as error:
                temporary.unlink(missing_ok=True)
                raise CaptureError(
                    "DOCUMENT_WRITE_FAILED",
                    "Capture 인덱스를 저장하지 못했습니다.",
                    http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from error

    def _entries(self) -> dict[str, CaptureIndexEntry]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return {
                capture_id: CaptureIndexEntry(
                    capture_id=item["captureId"],
                    capture_type=item["captureType"],
                    server_content_hash=item["serverContentHash"],
                    document_id=item["documentId"],
                    document_path=item["documentPath"],
                    created_at=item["createdAt"],
                    request_fingerprint=item["requestFingerprint"],
                    response=item["response"],
                )
                for capture_id, item in payload.items()
            }
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise CaptureError(
                "INTERNAL_ERROR",
                "Capture 인덱스를 읽지 못했습니다.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from error


def normalize_capture_text(value: str) -> str:
    """Apply the language-neutral capture normalization contract."""

    source = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not source:
        return ""
    output: list[str] = []
    in_code_block = False
    empty_lines = 0
    for line in source.split("\n"):
        processed = line if in_code_block else line.rstrip(" \t")
        if processed.strip().startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block and not processed:
            empty_lines += 1
            if empty_lines > 2:
                continue
        else:
            empty_lines = 0
        output.append(processed)
    while output and not output[-1]:
        output.pop()
    return "\n".join(output)


def contains_sensitive_content(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) <= 12 and re.fullmatch(r"\d{4,8}", stripped):
        return True
    return any(pattern.search(value) for pattern in SENSITIVE_PATTERNS)


def server_content_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_fingerprint(envelope: CaptureEnvelope) -> str:
    canonical = json.dumps(
        envelope.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ClipboardItemDocumentRenderer:
    TITLES = {
        SourceType.CHATGPT: "ChatGPT 답변",
        SourceType.CODEX: "Codex 답변",
        SourceType.GENERAL: "클립보드 문서",
    }

    def render(
        self,
        envelope: CaptureEnvelope,
        payload: ClipboardItemPayload,
        normalized: str,
        content_hash: str,
        document_id: str,
        stored_at: datetime,
    ) -> str:
        title = payload.title or self.TITLES[envelope.source_type]
        parent = envelope.parent_document
        properties: dict[str, Any] = {
            "id": document_id,
            "capture_id": envelope.capture_id,
            "schema_version": envelope.schema_version,
            "title": title,
            "aliases": [title],
            "source_type": envelope.source_type.value,
            "source_app": str(
                envelope.metadata.get("sourceApp", envelope.capture_method)
            ),
            "capture_type": envelope.capture_type.value,
            "capture_device": envelope.capture_device.value,
            "capture_method": envelope.capture_method,
            "captured_at": envelope.captured_at.isoformat(),
            "stored_at": stored_at.isoformat(),
            "project_id": envelope.project_id,
            "status": "inbox",
            "type": "reference",
            "reviewed": False,
            "tags": ["autoknowledge", envelope.source_type.value],
            "topics": ["[[MOC - AutoKnowledge]]"],
            "content_hash": content_hash,
            "parent_document": parent,
        }
        frontmatter = ["---"]
        for key, value in properties.items():
            frontmatter.append(
                f"{key}: {json.dumps(value, ensure_ascii=False)}"
                if value is not None
                else f"{key}: null"
            )
        frontmatter.extend(("---", "", f"# {title}", "", "## 원문", "", normalized, ""))
        if parent:
            frontmatter.extend(("## 연결", "", f"- 상위 문서: [[{parent}]]", ""))
        else:
            frontmatter.extend(("## 연결", "", "- [[MOC - AutoKnowledge]]", ""))
        return "\n".join(frontmatter)


class ClipboardItemHandler:
    def __init__(
        self,
        vault_dir: Path,
        index_store: CaptureIndexStore,
        *,
        indexer: KnowledgeIndexer | None = None,
        knowledge_source: str = "autoknowledge-vault",
    ) -> None:
        self.vault_dir = vault_dir.resolve()
        self.index_store = index_store
        self.renderer = ClipboardItemDocumentRenderer()
        self.indexer = indexer
        self.knowledge_source = knowledge_source
        self._lock = Lock()

    def supports(self, capture_type: CaptureType) -> bool:
        return capture_type == CaptureType.CLIPBOARD_ITEM

    def handle(self, envelope: CaptureEnvelope) -> CaptureResult:
        payload = ClipboardItemPayload.model_validate(envelope.payload)
        normalized = normalize_capture_text(payload.content)
        if not normalized:
            raise CaptureError(
                "CONTENT_EMPTY", "본문이 비어 있습니다.", field="payload.content"
            )
        if len(normalized.encode("utf-8")) > MAX_CLIPBOARD_BYTES:
            raise CaptureError(
                "CONTENT_TOO_LARGE",
                "본문은 1MB를 초과할 수 없습니다.",
                field="payload.content",
                http_status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        if contains_sensitive_content(normalized):
            raise CaptureError(
                "SENSITIVE_CONTENT_DETECTED",
                "민감정보가 감지되어 저장하지 않았습니다.",
                field="payload.content",
            )
        calculated_hash = server_content_hash(normalized)
        fingerprint = request_fingerprint(envelope)
        warnings: list[str] = []
        if calculated_hash != envelope.content_hash:
            warnings.append("CONTENT_HASH_MISMATCH")

        with self._lock:
            prior_capture = self.index_store.find_capture(envelope.capture_id)
            if prior_capture:
                if prior_capture.request_fingerprint != fingerprint:
                    raise CaptureError(
                        "DUPLICATE_CAPTURE_ID",
                        "같은 captureId에 다른 요청을 사용할 수 없습니다.",
                        field="captureId",
                        http_status=status.HTTP_409_CONFLICT,
                    )
                return CaptureResult.model_validate(prior_capture.response)

            prior_content = self.index_store.find_hash(calculated_hash)
            if prior_content:
                duplicate = CaptureResult(
                    status="duplicate",
                    captureId=envelope.capture_id,
                    documentId=prior_content.document_id,
                    documentPath=prior_content.document_path,
                    captureType=envelope.capture_type,
                    duplicate=True,
                    warnings=warnings,
                )
                self._record(envelope, calculated_hash, fingerprint, duplicate)
                return duplicate

            destination_dir = self._destination_dir(envelope.target_folder)
            document_id = f"doc_{uuid4().hex}"
            stored_at = datetime.now(timezone.utc)
            filename = (
                f"{envelope.captured_at.strftime('%Y-%m-%d-%H%M%S')}-"
                f"{envelope.source_type.value}-clip-{calculated_hash[:8]}.md"
            )
            destination = destination_dir / filename
            markdown = self.renderer.render(
                envelope,
                payload,
                normalized,
                calculated_hash,
                document_id,
                stored_at,
            )
            self._atomic_write(destination, markdown)
            relative_path = destination.relative_to(self.vault_dir).as_posix()
            indexed_document_id = self._index_and_link(
                envelope,
                relative_path,
                document_id,
                warnings,
            )
            result = CaptureResult(
                status="saved",
                captureId=envelope.capture_id,
                documentId=indexed_document_id,
                documentPath=relative_path,
                captureType=envelope.capture_type,
                duplicate=False,
                warnings=warnings,
            )
            self._record(envelope, calculated_hash, fingerprint, result)
            return result

    def _destination_dir(self, target_folder: str) -> Path:
        if target_folder not in ALLOWED_VAULT_FOLDERS:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "허용되지 않은 targetFolder입니다.",
                field="targetFolder",
            )
        relative = Path(target_folder)
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "targetFolder는 Vault 내부 상대 경로여야 합니다.",
                field="targetFolder",
            )
        destination = (self.vault_dir / relative).resolve()
        try:
            destination.relative_to(self.vault_dir)
        except ValueError as error:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "targetFolder가 Vault 밖을 가리킵니다.",
                field="targetFolder",
            ) from error
        return destination

    @staticmethod
    def _atomic_write(destination: Path, markdown: str) -> None:
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(markdown, encoding="utf-8")
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise CaptureError(
                "DOCUMENT_WRITE_FAILED",
                "Markdown 문서를 저장하지 못했습니다.",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from error

    def _index_and_link(
        self,
        envelope: CaptureEnvelope,
        relative_path: str,
        fallback_document_id: str,
        warnings: list[str],
    ) -> str:
        if self.indexer is None:
            if envelope.parent_document:
                warnings.append("PARENT_DOCUMENT_NOT_VERIFIED")
            return fallback_document_id
        try:
            indexed = self.indexer.index_file(self.knowledge_source, relative_path)
            document_id = str(indexed.get("documentId") or fallback_document_id)
        except Exception:  # External index failure must not remove the durable note.
            warnings.append("INDEX_UPDATE_FAILED")
            return fallback_document_id
        if envelope.parent_document:
            try:
                self.indexer.link_child(
                    self.knowledge_source,
                    envelope.parent_document,
                    document_id,
                )
            except Exception:
                warnings.append("PARENT_DOCUMENT_NOT_FOUND")
        return document_id

    def _record(
        self,
        envelope: CaptureEnvelope,
        content_hash: str,
        fingerprint: str,
        result: CaptureResult,
    ) -> None:
        self.index_store.add(
            CaptureIndexEntry(
                capture_id=envelope.capture_id,
                capture_type=envelope.capture_type.value,
                server_content_hash=content_hash,
                document_id=result.document_id or "",
                document_path=result.document_path or "",
                created_at=datetime.now(timezone.utc).isoformat(),
                request_fingerprint=fingerprint,
                response=result.model_dump(mode="json", by_alias=True),
            )
        )


class DevelopmentSessionDocumentRenderer:
    def render(
        self,
        envelope: CaptureEnvelope,
        payload: DevelopmentSessionPayload,
        document_id: str,
        revision: int,
    ) -> str:
        repository = payload.repository
        properties = {
            "id": document_id,
            "capture_id": envelope.capture_id,
            "schema_version": envelope.schema_version,
            "title": f"Codex 작업 — {payload.title}",
            "source_type": "codex",
            "capture_type": "development_session",
            "capture_device": envelope.capture_device.value,
            "capture_method": envelope.capture_method,
            "project_id": envelope.project_id,
            "repository": repository.name if repository else None,
            "branch_before": repository.branch_before if repository else None,
            "branch_after": repository.branch_after if repository else None,
            "head_before": repository.head_before if repository else None,
            "head_after": repository.head_after if repository else None,
            "started_at": payload.started_at.isoformat(),
            "ended_at": payload.ended_at.isoformat() if payload.ended_at else None,
            "status": "completed" if payload.ended_at else "in_progress",
            "changed_files_count": len(payload.changed_files),
            "revision": revision,
        }
        lines = ["---"]
        lines.extend(
            (
                f"{key}: {json.dumps(value, ensure_ascii=False)}"
                if value is not None
                else f"{key}: null"
            )
            for key, value in properties.items()
        )
        lines.extend(
            [
                "---",
                "",
                f"# Codex 작업 — {payload.title}",
                "",
                "## 작업 요청",
                "",
                payload.request or "기록되지 않음",
                "",
                "## 작업 요약",
                "",
                payload.summary or "기록되지 않음",
                "",
                "## 변경 파일",
                "",
            ]
        )
        lines.extend(
            f"- `{item.get('path', '-')}` — {item.get('changeType', 'unknown')} "
            f"({item.get('attribution', 'UNKNOWN_ATTRIBUTION')})"
            for item in payload.changed_files
        )
        lines.extend(("", "## Codex 대화", ""))
        messages = payload.messages
        displayed = messages
        if len(messages) > 200:
            important = [
                item
                for item in messages[20:-50]
                if item.get("messageType")
                in {"progress", "error", "approval_request", "approval_result"}
            ]
            displayed = messages[:20] + important + messages[-50:]
            lines.extend(
                (
                    f"> 전체 {len(messages)}개 메시지 중 일부만 표시합니다.",
                    "> 전체 대화는 로컬 messages.json에서 확인합니다.",
                    "",
                )
            )
        headings = {
            ("user", "text"): "사용자",
            ("assistant", "text"): "Codex",
            ("assistant", "progress"): "Codex 진행",
            ("system_summary", "progress"): "Codex 공개 요약",
        }
        for item in displayed:
            role = item.get("role", "unknown")
            message_type = item.get("messageType", "unknown")
            if role == "tool" and message_type == "command":
                command = str(item.get("content", "")).split("\n\n", 1)[0]
                lines.extend(("### 도구 실행", "", f"- `{command}`", ""))
                continue
            if role == "tool" and message_type not in {"error", "patch"}:
                continue
            heading = headings.get((role, message_type), f"공개 {message_type} 이벤트")
            lines.extend((f"### {heading}", "", str(item.get("content") or "-"), ""))
        lines.extend(
            (
                "",
                "## 실행 명령",
                "",
                "| 명령 | 분류 | 종료 코드 | 결과 |",
                "|---|---|---:|---|",
            )
        )
        lines.extend(
            f"| `{item.get('command', '-')}` | {item.get('category', 'GENERAL')} | "
            f"{item.get('exitCode', '-')} | {item.get('status', 'UNKNOWN')} |"
            for item in payload.commands
        )
        lines.extend(("", "## 첨부", ""))
        lines.extend(
            f"- [[{item.get('name', 'attachment')}]]" for item in payload.attachments
        )
        lines.append("")
        return "\n".join(lines)


class DevelopmentSessionHandler:
    def __init__(
        self,
        vault_dir: Path,
        index_store: CaptureIndexStore,
        *,
        indexer: KnowledgeIndexer | None = None,
        knowledge_source: str = "autoknowledge-vault",
    ) -> None:
        self.vault_dir = vault_dir.resolve()
        self.index_store = index_store
        self.indexer = indexer
        self.knowledge_source = knowledge_source
        self.renderer = DevelopmentSessionDocumentRenderer()
        self._lock = Lock()

    def supports(self, capture_type: CaptureType) -> bool:
        return capture_type == CaptureType.DEVELOPMENT_SESSION

    def handle(self, envelope: CaptureEnvelope) -> CaptureResult:
        payload = DevelopmentSessionPayload.model_validate(envelope.payload)
        self._validate_sensitive(payload.model_dump(mode="json", by_alias=True))
        fingerprint = request_fingerprint(envelope)
        calculated_hash = server_content_hash(
            json.dumps(
                envelope.payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        with self._lock:
            prior = self.index_store.find_capture(envelope.capture_id)
            if prior and prior.request_fingerprint == fingerprint:
                return CaptureResult.model_validate(prior.response)
            revision = int(prior.response.get("revision", 1)) + 1 if prior else 1
            destination_dir = self._destination_dir(envelope.target_folder)
            document_id = f"doc_{uuid4().hex}"
            filename = (
                f"{envelope.captured_at.strftime('%Y-%m-%d-%H%M%S')}-codex-session-"
                f"{calculated_hash[:8]}-r{revision}.md"
            )
            destination = destination_dir / filename
            self._atomic_write(
                destination,
                self.renderer.render(envelope, payload, document_id, revision),
            )
            self._write_attachments(destination.with_suffix(""), payload.attachments)
            relative_path = destination.relative_to(self.vault_dir).as_posix()
            warnings: list[str] = []
            if calculated_hash != envelope.content_hash:
                warnings.append("CONTENT_HASH_MISMATCH")
            if prior:
                warnings.append("SESSION_REVISION_CREATED")
            result = CaptureResult(
                status="saved",
                captureId=envelope.capture_id,
                documentId=document_id,
                documentPath=relative_path,
                captureType=envelope.capture_type,
                duplicate=False,
                revision=revision,
                warnings=warnings,
            )
            self.index_store.add(
                CaptureIndexEntry(
                    capture_id=envelope.capture_id,
                    capture_type=envelope.capture_type.value,
                    server_content_hash=calculated_hash,
                    document_id=document_id,
                    document_path=relative_path,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    request_fingerprint=fingerprint,
                    response=result.model_dump(mode="json", by_alias=True),
                )
            )
            if self.indexer is not None:
                try:
                    self.indexer.index_file(self.knowledge_source, relative_path)
                except Exception:
                    result.warnings.append("INDEX_UPDATE_FAILED")
            return result

    def _destination_dir(self, target_folder: str) -> Path:
        normalized = target_folder.replace("\\", "/").strip("/")
        root_name = normalized.split("/", 1)[0]
        if root_name not in ALLOWED_VAULT_FOLDERS:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "허용되지 않은 targetFolder입니다.",
                field="targetFolder",
            )
        relative = Path(normalized)
        if relative.is_absolute() or relative.drive or ".." in relative.parts:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "targetFolder가 안전하지 않습니다.",
                field="targetFolder",
            )
        destination = (self.vault_dir / relative).resolve()
        try:
            destination.relative_to(self.vault_dir)
        except ValueError as error:
            raise CaptureError(
                "INVALID_TARGET_FOLDER",
                "targetFolder가 Vault 밖을 가리킵니다.",
                field="targetFolder",
            ) from error
        return destination

    @staticmethod
    def _validate_sensitive(value: Any) -> None:
        if isinstance(value, str):
            # Preserve a short separator so text following an intentionally masked
            # assignment is not mistaken for the secret value itself.
            candidate = value.replace("[REDACTED]", "***")
            if candidate and contains_sensitive_content(candidate):
                raise CaptureError(
                    "SENSITIVE_CONTENT_DETECTED",
                    "민감정보가 감지되어 개발 세션을 저장하지 않았습니다.",
                )
        elif isinstance(value, dict):
            for nested in value.values():
                DevelopmentSessionHandler._validate_sensitive(nested)
        elif isinstance(value, list):
            for nested in value:
                DevelopmentSessionHandler._validate_sensitive(nested)

    @staticmethod
    def _atomic_write(destination: Path, content: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            os.replace(temporary, destination)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise CaptureError(
                "DOCUMENT_WRITE_FAILED",
                "개발 세션 문서를 저장하지 못했습니다.",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from error

    @staticmethod
    def _write_attachments(
        destination: Path, attachments: list[dict[str, Any]]
    ) -> None:
        for attachment in attachments:
            name = Path(str(attachment.get("name", "attachment.txt"))).name
            content = attachment.get("content")
            if not isinstance(content, str):
                continue
            DevelopmentSessionHandler._validate_sensitive(content)
            if len(content.encode("utf-8")) > 5 * 1024 * 1024:
                raise CaptureError(
                    "ATTACHMENT_TOO_LARGE", "첨부 파일은 5MB 이하여야 합니다."
                )
            DevelopmentSessionHandler._atomic_write(destination / name, content)


class CaptureApplicationService:
    def __init__(self, registry: CaptureHandlerRegistry) -> None:
        self.registry = registry

    def capture(self, envelope: CaptureEnvelope) -> CaptureResult:
        return self.registry.resolve(envelope.capture_type).handle(envelope)


def create_capture_service(
    vault_dir: Path,
    data_dir: Path,
    *,
    indexer: KnowledgeIndexer | None = None,
    knowledge_source: str = "autoknowledge-vault",
) -> CaptureApplicationService:
    index_store = CaptureIndexStore(data_dir / "capture-index-v1.json")
    return CaptureApplicationService(
        CaptureHandlerRegistry(
            (
                ClipboardItemHandler(
                    vault_dir,
                    index_store,
                    indexer=indexer,
                    knowledge_source=knowledge_source,
                ),
                DevelopmentSessionHandler(
                    vault_dir,
                    index_store,
                    indexer=indexer,
                    knowledge_source=knowledge_source,
                ),
            )
        )
    )


def legacy_share_to_envelope(request: Any, capture_id: str) -> CaptureEnvelope:
    captured_at = request.captured_at or request.shared_at or datetime.now(timezone.utc)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    content = normalize_capture_text(request.content)
    return CaptureEnvelope(
        schemaVersion=SCHEMA_VERSION,
        captureId=f"cap_{capture_id}",
        sourceType=request.source_type or SourceType.GENERAL,
        captureType=CaptureType.CLIPBOARD_ITEM,
        captureDevice=CaptureDevice.ANDROID,
        captureMethod="android_clipboard",
        projectId=None,
        targetFolder=request.target_folder,
        parentDocument=request.parent_document_id,
        capturedAt=captured_at,
        deviceId=request.device_id or f"legacy-{capture_id[:8]}",
        contentHash=request.content_hash or server_content_hash(content),
        metadata={"sourceApp": request.source_app or "android_clipboard"},
        payload={
            "content": request.content,
            "title": request.title,
            "mimeType": "text/plain",
            "language": None,
        },
    )


def install_capture_api(
    application: FastAPI,
    service: CaptureApplicationService,
) -> None:
    @application.exception_handler(RequestValidationError)
    async def capture_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        if request.url.path != "/api/v1/captures":
            return await request_validation_exception_handler(request, error)
        first = error.errors()[0] if error.errors() else {}
        location = first.get("loc", ())
        field = ".".join(str(item) for item in location if item != "body") or None
        code = _validation_code(field, str(first.get("msg", "")))
        response = CaptureErrorResponse(
            error=CaptureErrorDetail(
                code=code,
                message="Capture 요청이 유효하지 않습니다.",
                field=field,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response.model_dump(mode="json"),
        )

    @application.post(
        "/api/v1/captures",
        response_model=CaptureResult,
        responses={
            409: {"model": CaptureErrorResponse},
            422: {"model": CaptureErrorResponse},
            501: {"model": CaptureErrorResponse},
            503: {"model": CaptureErrorResponse},
        },
    )
    def create_capture(envelope: CaptureEnvelope) -> CaptureResult | JSONResponse:
        try:
            result = service.capture(envelope)
        except CaptureError as error:
            return JSONResponse(
                status_code=error.http_status,
                content=error.response().model_dump(mode="json"),
            )
        return result


def _validation_code(field: str | None, message: str) -> str:
    if field == "schemaVersion":
        return "INVALID_SCHEMA_VERSION"
    if field == "captureType":
        return "INVALID_CAPTURE_TYPE"
    if field == "sourceType":
        return "INVALID_SOURCE_TYPE"
    if field == "captureDevice":
        return "INVALID_CAPTURE_DEVICE"
    if field == "targetFolder":
        return "INVALID_TARGET_FOLDER"
    if field and field.endswith("content") and "missing" in message.lower():
        return "CONTENT_EMPTY"
    return "INVALID_PAYLOAD"
