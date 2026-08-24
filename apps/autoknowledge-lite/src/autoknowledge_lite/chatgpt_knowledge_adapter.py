"""Read-only projection from ChatGPT source data to the common knowledge model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from autoknowledge_lite.capture_api import (
    CaptureEnvelope,
    CaptureType,
    ClipboardItemPayload,
    SourceType,
    normalize_capture_text,
    server_content_hash,
)
from autoknowledge_lite.knowledge_model import (
    Activity,
    DataSource,
    DerivationMethod,
    KnowledgeModel,
    Message,
    MessageRole,
    Provenance,
    Session,
    SessionSource,
    Task,
)
from autoknowledge_lite.task_analyzer import (
    SessionTaskAnalyzer,
    TaskBoundaryCandidate,
)


class ChatGPTKnowledgeProjection(KnowledgeModel):
    """Structured records projected from one ChatGPT source."""

    session: Session
    messages: tuple[Message, ...]
    tasks: tuple[Task, ...] = ()
    activities: tuple[Activity, ...] = ()
    boundary_candidates: tuple[TaskBoundaryCandidate, ...] = ()
    analysis_warnings: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class ChatGPTKnowledgeAdapterError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ChatGPTKnowledgeAdapter:
    """Project ChatGPT exports and existing clips without changing their input."""

    _ROLE_MAP = {
        "user": MessageRole.USER,
        "assistant": MessageRole.ASSISTANT,
        "tool": MessageRole.TOOL,
        "system": MessageRole.SYSTEM,
    }

    def __init__(self, *, task_analyzer: SessionTaskAnalyzer | None = None) -> None:
        self.task_analyzer = task_analyzer or SessionTaskAnalyzer()

    def project(
        self, source: CaptureEnvelope | Mapping[str, Any]
    ) -> ChatGPTKnowledgeProjection:
        if isinstance(source, CaptureEnvelope):
            return self._project_clip(source)
        if not isinstance(source, Mapping):
            raise ChatGPTKnowledgeAdapterError(
                "INVALID_CHATGPT_SOURCE", "ChatGPT source must be a capture or mapping"
            )
        if "schemaVersion" in source or "schema_version" in source:
            try:
                envelope = CaptureEnvelope.model_validate(source)
            except ValidationError as error:
                raise ChatGPTKnowledgeAdapterError(
                    "INVALID_CHATGPT_CLIP", "ChatGPT clip envelope is invalid"
                ) from error
            return self._project_clip(envelope)
        return self._project_export(source)

    def _project_clip(self, envelope: CaptureEnvelope) -> ChatGPTKnowledgeProjection:
        if envelope.source_type != SourceType.CHATGPT:
            raise ChatGPTKnowledgeAdapterError(
                "INVALID_CHATGPT_SOURCE",
                "ChatGPT projection requires sourceType=chatgpt",
            )
        if envelope.capture_type != CaptureType.CLIPBOARD_ITEM:
            raise ChatGPTKnowledgeAdapterError(
                "INVALID_CHATGPT_CAPTURE_TYPE",
                "ChatGPT clip projection requires captureType=clipboard_item",
            )
        try:
            payload = ClipboardItemPayload.model_validate(envelope.payload)
        except ValidationError as error:
            raise ChatGPTKnowledgeAdapterError(
                "INVALID_CHATGPT_CLIP", "ChatGPT clip payload is invalid"
            ) from error

        warnings: list[str] = []
        title = payload.title
        if title is None or not title.strip():
            title = envelope.capture_id
            warnings.append("CHATGPT_CLIP_TITLE_MISSING")
        session_ref = f"capture:{envelope.capture_id}"
        provenance = self._rule_provenance(session_ref)
        message = Message(
            message_id=envelope.capture_id,
            session_id=envelope.capture_id,
            role=MessageRole.ASSISTANT,
            content=payload.content,
            sequence=1,
            content_hash=envelope.content_hash,
            provenance=self._rule_provenance(
                session_ref, f"message:{envelope.capture_id}"
            ),
        )
        session = Session(
            session_id=envelope.capture_id,
            source=SessionSource.CHATGPT,
            title=title,
            created_at=envelope.captured_at,
            updated_at=envelope.captured_at,
            capture_id=envelope.capture_id,
            document_id=self._optional_text(envelope.metadata.get("documentId")),
            message_ids=(message.message_id,),
            metadata={
                "capture_method": envelope.capture_method,
                "capture_type": envelope.capture_type.value,
            },
            provenance=provenance,
        )
        return ChatGPTKnowledgeProjection(
            session=session,
            messages=(message,),
            warnings=tuple(warnings),
        )

    def _project_export(self, source: Mapping[str, Any]) -> ChatGPTKnowledgeProjection:
        declared_source = source.get("source")
        if declared_source is not None and str(declared_source).casefold() != "chatgpt":
            raise ChatGPTKnowledgeAdapterError(
                "INVALID_CHATGPT_SOURCE",
                "Source explicitly identifies a non-ChatGPT session",
            )
        session_id = self._required_text(
            source.get("id") or source.get("conversation_id"),
            "CHATGPT_SESSION_ID_MISSING",
            "ChatGPT session id is missing",
        )
        title = self._required_text(
            source.get("title"),
            "CHATGPT_SESSION_TITLE_MISSING",
            "ChatGPT session title is missing",
        )
        created_at = self._required_timestamp(
            source.get("create_time") or source.get("created_at"),
            "CHATGPT_SESSION_CREATED_AT_INVALID",
            "ChatGPT session create time is missing or invalid",
        )
        updated_at = self._required_timestamp(
            source.get("update_time") or source.get("updated_at"),
            "CHATGPT_SESSION_UPDATED_AT_INVALID",
            "ChatGPT session update time is missing or invalid",
        )
        if updated_at < created_at:
            raise ChatGPTKnowledgeAdapterError(
                "CHATGPT_SESSION_TIME_RANGE_INVALID",
                "ChatGPT session update time precedes create time",
            )

        session_ref = f"chatgpt-session:{session_id}"
        ordered_messages, warnings = self._ordered_source_messages(source)
        messages = self._project_messages(
            session_id, ordered_messages, session_ref, warnings
        )
        source_file = self._optional_text(
            source.get("source_file") or source.get("sourceFile")
        )
        session = Session(
            session_id=session_id,
            source=SessionSource.CHATGPT,
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            source_file=source_file,
            source_session_id=session_id,
            message_ids=tuple(message.message_id for message in messages),
            provenance=self._original_provenance(session_ref),
        )
        analysis = self.task_analyzer.analyze(session, messages)
        session = session.model_copy(
            update={"task_ids": tuple(task.task_id for task in analysis.tasks)}
        )
        return ChatGPTKnowledgeProjection(
            session=session,
            messages=messages,
            tasks=analysis.tasks,
            activities=analysis.activities,
            boundary_candidates=analysis.boundary_candidates,
            analysis_warnings=analysis.warnings,
            warnings=tuple(sorted(set(warnings))),
        )

    def _ordered_source_messages(
        self, source: Mapping[str, Any]
    ) -> tuple[list[Mapping[str, Any]], list[str]]:
        warnings: list[str] = []
        mapping = source.get("mapping")
        if isinstance(mapping, Mapping):
            current_node = source.get("current_node") or source.get("currentNode")
            if not isinstance(current_node, str) or not current_node:
                warnings.append("CHATGPT_CURRENT_NODE_MISSING")
                return [], warnings
            ordered: list[Mapping[str, Any]] = []
            visited: set[str] = set()
            node_id: str | None = current_node
            while node_id is not None:
                if node_id in visited:
                    warnings.append("CHATGPT_MESSAGE_TREE_CYCLE")
                    break
                visited.add(node_id)
                node = mapping.get(node_id)
                if not isinstance(node, Mapping):
                    warnings.append("CHATGPT_MESSAGE_NODE_INVALID")
                    break
                message = node.get("message")
                if isinstance(message, Mapping):
                    ordered.append(message)
                elif message is not None:
                    warnings.append("CHATGPT_MESSAGE_RECORD_INVALID")
                parent = node.get("parent")
                if parent is not None and not isinstance(parent, str):
                    warnings.append("CHATGPT_MESSAGE_PARENT_INVALID")
                    break
                node_id = parent
            ordered.reverse()
            return ordered, warnings

        messages = source.get("messages")
        if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes)):
            valid = []
            for message in messages:
                if isinstance(message, Mapping):
                    valid.append(message)
                else:
                    warnings.append("CHATGPT_MESSAGE_RECORD_INVALID")
            return valid, warnings
        warnings.append("CHATGPT_MESSAGES_MISSING")
        return [], warnings

    def _project_messages(
        self,
        session_id: str,
        source_messages: list[Mapping[str, Any]],
        session_ref: str,
        warnings: list[str],
    ) -> tuple[Message, ...]:
        projected: list[Message] = []
        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()
        for source_sequence, source_message in enumerate(source_messages, 1):
            message_id = source_message.get("id") or source_message.get("message_id")
            if not isinstance(message_id, str) or not message_id:
                warnings.append("CHATGPT_MESSAGE_ID_MISSING")
                continue
            if message_id in seen_ids:
                warnings.append("CHATGPT_MESSAGE_ID_DUPLICATE")
                continue
            role = self._message_role(source_message)
            if role is None:
                warnings.append("CHATGPT_MESSAGE_ROLE_UNSUPPORTED")
                continue
            content = self._message_content(source_message)
            if content is None:
                warnings.append("CHATGPT_MESSAGE_CONTENT_MISSING")
                continue
            comparison_hash = server_content_hash(normalize_capture_text(content))
            if comparison_hash in seen_hashes:
                warnings.append("CHATGPT_MESSAGE_CONTENT_DUPLICATE")
                continue
            timestamp = self._optional_timestamp(
                source_message.get("create_time") or source_message.get("created_at"),
                warnings,
                "CHATGPT_MESSAGE_TIMESTAMP_INVALID",
            )
            supplied_hash = source_message.get("contentHash") or source_message.get(
                "content_hash"
            )
            content_hash = supplied_hash if self._valid_hash(supplied_hash) else None
            if supplied_hash is not None and content_hash is None:
                warnings.append("CHATGPT_MESSAGE_HASH_INVALID")
            projected.append(
                Message(
                    message_id=message_id,
                    session_id=session_id,
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    sequence=source_sequence,
                    source_message_id=message_id,
                    content_hash=content_hash,
                    provenance=self._original_provenance(
                        session_ref, f"source-message:{message_id}"
                    ),
                )
            )
            seen_ids.add(message_id)
            seen_hashes.add(comparison_hash)
        return tuple(projected)

    def _message_role(self, source_message: Mapping[str, Any]) -> MessageRole | None:
        author = source_message.get("author")
        raw_role = author.get("role") if isinstance(author, Mapping) else None
        if raw_role is None:
            raw_role = source_message.get("role")
        return self._ROLE_MAP.get(str(raw_role or "").casefold())

    @staticmethod
    def _message_content(source_message: Mapping[str, Any]) -> str | None:
        content = source_message.get("content")
        if isinstance(content, str):
            return content
        if not isinstance(content, Mapping):
            return None
        parts = content.get("parts")
        if (
            isinstance(parts, Sequence)
            and not isinstance(parts, (str, bytes))
            and len(parts) == 1
            and isinstance(parts[0], str)
        ):
            return parts[0]
        return None

    @classmethod
    def _required_timestamp(cls, value: Any, code: str, message: str) -> datetime:
        parsed = cls._parse_timestamp(value)
        if parsed is None:
            raise ChatGPTKnowledgeAdapterError(code, message)
        return parsed

    @classmethod
    def _optional_timestamp(
        cls, value: Any, warnings: list[str], warning_code: str
    ) -> datetime | None:
        if value is None:
            return None
        parsed = cls._parse_timestamp(value)
        if parsed is None:
            warnings.append(warning_code)
        return parsed

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed

    @staticmethod
    def _required_text(value: Any, code: str, message: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ChatGPTKnowledgeAdapterError(code, message)
        return value

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _original_provenance(*source_refs: str) -> Provenance:
        return Provenance(source=DataSource.ORIGINAL, source_refs=source_refs)

    @staticmethod
    def _rule_provenance(*source_refs: str) -> Provenance:
        return Provenance(
            source=DataSource.DERIVED,
            derived_by=DerivationMethod.RULE,
            confidence=1.0,
            source_refs=source_refs,
        )

    @staticmethod
    def _valid_hash(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 64:
            return False
        return all(character in "0123456789abcdef" for character in value)
