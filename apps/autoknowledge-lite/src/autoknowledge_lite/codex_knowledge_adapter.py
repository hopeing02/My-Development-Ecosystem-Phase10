"""Read-only projection from Codex captures to the common knowledge model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import ValidationError

from autoknowledge_lite.capture_api import (
    CaptureEnvelope,
    CaptureType,
    DevelopmentSessionPayload,
    SourceType,
)
from autoknowledge_lite.knowledge_model import (
    Activity,
    ActivityType,
    CommandRecord,
    DataSource,
    DerivationMethod,
    FileChangeType,
    FileRecord,
    KnowledgeModel,
    Message,
    MessageRole,
    Provenance,
    Session,
    SessionSource,
    TestRecord,
    TestStatus,
)


class CodexKnowledgeProjection(KnowledgeModel):
    session: Session
    messages: tuple[Message, ...]
    task_id: str
    activities: tuple[Activity, ...] = ()
    commands: tuple[CommandRecord, ...] = ()
    files: tuple[FileRecord, ...] = ()
    tests: tuple[TestRecord, ...] = ()
    warnings: tuple[str, ...] = ()


class CodexKnowledgeAdapterError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CodexKnowledgeAdapter:
    """Projects validated Codex captures without changing their source payload."""

    _ROLE_MAP = {
        "user": MessageRole.USER,
        "assistant": MessageRole.ASSISTANT,
        "tool": MessageRole.TOOL,
        "system": MessageRole.SYSTEM,
        "system_summary": MessageRole.SYSTEM,
    }

    def project(self, envelope: CaptureEnvelope) -> CodexKnowledgeProjection:
        if envelope.source_type != SourceType.CODEX:
            raise CodexKnowledgeAdapterError(
                "INVALID_CODEX_SOURCE", "Codex projection requires sourceType=codex"
            )
        if envelope.capture_type != CaptureType.DEVELOPMENT_SESSION:
            raise CodexKnowledgeAdapterError(
                "INVALID_CODEX_CAPTURE_TYPE",
                "Codex projection requires captureType=development_session",
            )
        try:
            payload = DevelopmentSessionPayload.model_validate(envelope.payload)
        except ValidationError as error:
            raise CodexKnowledgeAdapterError(
                "INVALID_CODEX_SESSION_PAYLOAD", "Codex session payload is invalid"
            ) from error

        session_id = payload.capture_session_id or envelope.capture_id
        session_ref = f"capture:{envelope.capture_id}"
        session_provenance = Provenance(
            source=DataSource.ORIGINAL,
            source_refs=(session_ref,),
        )
        messages, warnings = self._project_messages(
            session_id, payload.messages, session_ref
        )
        task_id = f"task:{envelope.capture_id}:session"
        commands = self._project_commands(
            task_id, payload.commands, session_ref, warnings
        )
        files = self._project_files(
            task_id, envelope.capture_id, payload.changed_files, session_ref, warnings
        )
        tests = self._project_tests(
            task_id, envelope.capture_id, payload.tests, commands, session_ref, warnings
        )
        activities = self._project_activities(
            task_id, commands, files, tests, session_ref
        )
        updated_at = payload.ended_at or envelope.captured_at
        metadata: dict[str, object] = {
            "client_type": payload.client_type,
            "capture_method": envelope.capture_method,
        }
        if payload.adapter is not None:
            metadata["adapter"] = payload.adapter
        if payload.repository is not None:
            metadata["repository"] = payload.repository.model_dump(
                mode="json", by_alias=True
            )

        session = Session(
            session_id=session_id,
            source=SessionSource.CODEX,
            title=payload.title,
            created_at=payload.started_at,
            updated_at=updated_at,
            source_session_id=payload.source_session_id,
            capture_id=envelope.capture_id,
            message_ids=tuple(message.message_id for message in messages),
            task_ids=(task_id,),
            metadata=metadata,
            provenance=session_provenance,
        )
        return CodexKnowledgeProjection(
            session=session,
            messages=messages,
            task_id=task_id,
            activities=activities,
            commands=commands,
            files=files,
            tests=tests,
            warnings=tuple(sorted(set(warnings))),
        )

    def _project_commands(
        self,
        task_id: str,
        source_commands: list[dict[str, Any]],
        session_ref: str,
        warnings: list[str],
    ) -> tuple[CommandRecord, ...]:
        projected: list[CommandRecord] = []
        seen_ids: set[str] = set()
        for index, source_command in enumerate(source_commands, 1):
            command = source_command.get("command")
            if not isinstance(command, str) or not command.strip():
                warnings.append("CODEX_COMMAND_TEXT_MISSING")
                continue
            source_id = source_command.get("commandId")
            command_id = (
                source_id
                if isinstance(source_id, str) and source_id
                else f"command:{task_id}:{index:03d}"
            )
            if command_id in seen_ids:
                warnings.append("CODEX_COMMAND_ID_DUPLICATE")
                continue
            started_at = self._timestamp(
                source_command.get("startedAt"),
                warnings,
                "CODEX_COMMAND_TIMESTAMP_INVALID",
            )
            completed_at = self._timestamp(
                source_command.get("endedAt") or source_command.get("completedAt"),
                warnings,
                "CODEX_COMMAND_TIMESTAMP_INVALID",
            )
            if started_at and completed_at and completed_at < started_at:
                warnings.append("CODEX_COMMAND_TIME_RANGE_INVALID")
                completed_at = None
            projected.append(
                CommandRecord(
                    command_id=command_id,
                    task_id=task_id,
                    command=command,
                    started_at=started_at,
                    completed_at=completed_at,
                    exit_code=self._integer(source_command.get("exitCode")),
                    stdout=self._text(source_command.get("stdout")),
                    stderr=self._text(source_command.get("stderr")),
                    provenance=self._original_provenance(
                        session_ref, f"command:{command_id}"
                    ),
                )
            )
            seen_ids.add(command_id)
        return tuple(projected)

    def _project_files(
        self,
        task_id: str,
        capture_id: str,
        source_files: list[dict[str, Any]],
        session_ref: str,
        warnings: list[str],
    ) -> tuple[FileRecord, ...]:
        projected: list[FileRecord] = []
        for index, source_file in enumerate(source_files, 1):
            path = source_file.get("path")
            if not isinstance(path, str) or not path.strip():
                warnings.append("CODEX_FILE_PATH_MISSING")
                continue
            try:
                change_type = FileChangeType(
                    str(source_file.get("changeType") or "").casefold()
                )
            except ValueError:
                warnings.append("CODEX_FILE_CHANGE_TYPE_UNSUPPORTED")
                continue
            previous_path = source_file.get("oldPath") or source_file.get(
                "previousPath"
            )
            if not isinstance(previous_path, str) or not previous_path:
                previous_path = None
            if change_type == FileChangeType.RENAMED and previous_path is None:
                warnings.append("CODEX_FILE_RENAME_SOURCE_MISSING")
                continue
            file_id = f"file:{capture_id}:{index:03d}"
            projected.append(
                FileRecord(
                    file_id=file_id,
                    task_id=task_id,
                    path=path,
                    change_type=change_type,
                    previous_path=previous_path,
                    content_hash=(
                        source_file.get("contentHash")
                        if self._valid_hash(source_file.get("contentHash"))
                        else None
                    ),
                    added_lines=self._non_negative_integer(
                        source_file.get("addedLines")
                    ),
                    deleted_lines=self._non_negative_integer(
                        source_file.get("deletedLines")
                    ),
                    provenance=self._original_provenance(
                        session_ref, f"changed-file:{index}"
                    ),
                )
            )
        return tuple(projected)

    def _project_tests(
        self,
        task_id: str,
        capture_id: str,
        source_tests: list[dict[str, Any]],
        commands: tuple[CommandRecord, ...],
        session_ref: str,
        warnings: list[str],
    ) -> tuple[TestRecord, ...]:
        projected: list[TestRecord] = []
        commands_by_id = {item.command_id: item for item in commands}
        seen_ids: set[str] = set()
        status_map = {
            "passed": TestStatus.PASSED,
            "failed": TestStatus.FAILED,
            "skipped": TestStatus.SKIPPED,
            "error": TestStatus.ERROR,
            "timed_out": TestStatus.ERROR,
            "timedout": TestStatus.ERROR,
            "cancelled": TestStatus.ERROR,
            "partial": TestStatus.ERROR,
            "unknown": TestStatus.ERROR,
        }
        for index, source_test in enumerate(source_tests, 1):
            source_id = source_test.get("testId")
            test_id = (
                source_id
                if isinstance(source_id, str) and source_id
                else f"test:{capture_id}:{index:03d}"
            )
            if test_id in seen_ids:
                warnings.append("CODEX_TEST_ID_DUPLICATE")
                continue
            linked_id = source_test.get("commandId")
            linked_command = (
                commands_by_id.get(linked_id) if isinstance(linked_id, str) else None
            )
            command = source_test.get("command")
            if not isinstance(command, str) or not command.strip():
                command = linked_command.command if linked_command else None
            if not command:
                warnings.append("CODEX_TEST_COMMAND_MISSING")
                continue
            raw_status = str(source_test.get("status") or "unknown").casefold()
            status = status_map.get(raw_status)
            if status is None:
                warnings.append("CODEX_TEST_STATUS_UNSUPPORTED")
                continue
            started_at = self._timestamp(
                source_test.get("startedAt"), warnings, "CODEX_TEST_TIMESTAMP_INVALID"
            )
            completed_at = self._timestamp(
                source_test.get("endedAt") or source_test.get("completedAt"),
                warnings,
                "CODEX_TEST_TIMESTAMP_INVALID",
            )
            if started_at and completed_at and completed_at < started_at:
                warnings.append("CODEX_TEST_TIME_RANGE_INVALID")
                completed_at = None
            output = source_test.get("output")
            if not isinstance(output, str):
                output = linked_command.stdout if linked_command else None
            projected.append(
                TestRecord(
                    test_id=test_id,
                    task_id=task_id,
                    command=command,
                    started_at=started_at
                    or (linked_command.started_at if linked_command else None),
                    completed_at=completed_at
                    or (linked_command.completed_at if linked_command else None),
                    exit_code=(
                        self._integer(source_test.get("exitCode"))
                        if source_test.get("exitCode") is not None
                        else linked_command.exit_code if linked_command else None
                    ),
                    status=status,
                    output=output,
                    command_id=linked_command.command_id if linked_command else None,
                    provenance=self._original_provenance(
                        session_ref, f"test:{test_id}"
                    ),
                )
            )
            seen_ids.add(test_id)
        return tuple(projected)

    @staticmethod
    def _project_activities(
        task_id: str,
        commands: tuple[CommandRecord, ...],
        files: tuple[FileRecord, ...],
        tests: tuple[TestRecord, ...],
        session_ref: str,
    ) -> tuple[Activity, ...]:
        entities = [
            (ActivityType.COMMAND, item.command_id, item.started_at, item.command)
            for item in commands
        ]
        entities.extend(
            (ActivityType.FILE_CHANGE, item.file_id, None, item.path) for item in files
        )
        entities.extend(
            (ActivityType.TEST, item.test_id, item.started_at, item.command)
            for item in tests
        )
        return tuple(
            Activity(
                activity_id=f"activity:{entity_id}",
                task_id=task_id,
                activity_type=activity_type,
                sequence=sequence,
                timestamp=timestamp,
                summary=summary,
                entity_refs=(entity_id,),
                provenance=Provenance(
                    source=DataSource.DERIVED,
                    derived_by=DerivationMethod.RULE,
                    confidence=1.0,
                    source_refs=(session_ref, entity_id),
                ),
            )
            for sequence, (activity_type, entity_id, timestamp, summary) in enumerate(
                entities, 1
            )
        )

    def _project_messages(
        self,
        session_id: str,
        source_messages: list[dict[str, Any]],
        session_ref: str,
    ) -> tuple[tuple[Message, ...], list[str]]:
        projected: list[Message] = []
        warnings: list[str] = []
        seen_ids: set[str] = set()
        for source_message in source_messages:
            message_id = source_message.get("messageId")
            if not isinstance(message_id, str) or not message_id:
                warnings.append("CODEX_MESSAGE_ID_MISSING")
                continue
            if message_id in seen_ids:
                warnings.append("CODEX_MESSAGE_ID_DUPLICATE")
                continue
            sequence = source_message.get("sequence")
            if (
                not isinstance(sequence, int)
                or isinstance(sequence, bool)
                or sequence < 1
            ):
                warnings.append("CODEX_MESSAGE_SEQUENCE_INVALID")
                continue
            content = source_message.get("content")
            if not isinstance(content, str):
                warnings.append("CODEX_MESSAGE_CONTENT_MISSING")
                continue
            role = self._ROLE_MAP.get(str(source_message.get("role") or ""))
            if role is None:
                warnings.append("CODEX_MESSAGE_ROLE_UNSUPPORTED")
                continue
            timestamp = self._timestamp(
                source_message.get("createdAt"),
                warnings,
                "CODEX_MESSAGE_TIMESTAMP_INVALID",
            )
            content_hash = source_message.get("contentHash")
            if not self._valid_hash(content_hash):
                if content_hash is not None:
                    warnings.append("CODEX_MESSAGE_HASH_INVALID")
                content_hash = None
            source_message_id = source_message.get("sourceMessageId")
            if not isinstance(source_message_id, str) or not source_message_id:
                source_message_id = None
            source_refs = [session_ref, f"message:{message_id}"]
            if source_message_id:
                source_refs.append(f"source-message:{source_message_id}")
            projected.append(
                Message(
                    message_id=message_id,
                    session_id=session_id,
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    sequence=sequence,
                    source_message_id=source_message_id,
                    content_hash=content_hash,
                    provenance=Provenance(
                        source=DataSource.ORIGINAL,
                        source_refs=tuple(source_refs),
                    ),
                )
            )
            seen_ids.add(message_id)
        return tuple(projected), warnings

    @staticmethod
    def _timestamp(
        value: Any, warnings: list[str], warning_code: str
    ) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                warnings.append(warning_code)
                return None
        else:
            warnings.append(warning_code)
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            warnings.append(warning_code)
            return None
        return parsed

    @staticmethod
    def _original_provenance(*source_refs: str) -> Provenance:
        return Provenance(source=DataSource.ORIGINAL, source_refs=source_refs)

    @staticmethod
    def _integer(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @classmethod
    def _non_negative_integer(cls, value: Any) -> int | None:
        parsed = cls._integer(value)
        return parsed if parsed is not None and parsed >= 0 else None

    @staticmethod
    def _text(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _valid_hash(value: Any) -> bool:
        if not isinstance(value, str) or len(value) != 64:
            return False
        return all(character in "0123456789abcdef" for character in value)
