"""Local, read-only discovery of sessions in ChatGPT data export archives."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

DEFAULT_MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_MEMBER_COUNT = 20_000
DEFAULT_MAX_JSON_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024
CONVERSATION_FILE_PATTERN = re.compile(
    r"^conversations(?:[-_]\d+)?\.json$", re.IGNORECASE
)


class ChatGPTSessionSourceError(RuntimeError):
    """Raised when an export archive cannot be inspected safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChatGPTSourceWarning:
    code: str
    source_member: str
    source_index: int | None = None


@dataclass(frozen=True)
class ChatGPTSessionReference:
    source_session_id: str
    title: str | None
    source_member: str
    source_index: int
    source_format: str = "chatgpt_export"


@dataclass(frozen=True)
class ChatGPTSourceDiscovery:
    archive_path: Path
    archive_sha256: str
    sessions: tuple[ChatGPTSessionReference, ...]
    warnings: tuple[ChatGPTSourceWarning, ...] = ()


class ChatGPTSessionSource(Protocol):
    source_type: str

    def discover_sessions(self) -> ChatGPTSourceDiscovery: ...

    def read_session(self, session_ref: ChatGPTSessionReference) -> dict[str, Any]: ...

    def supports(self, session_ref: ChatGPTSessionReference) -> bool: ...


class ChatGPTExportSource:
    """Inspect an explicitly selected ChatGPT export ZIP without extracting it."""

    source_type = "chatgpt"

    def __init__(
        self,
        archive_path: Path,
        *,
        max_archive_bytes: int = DEFAULT_MAX_ARCHIVE_BYTES,
        max_member_count: int = DEFAULT_MAX_MEMBER_COUNT,
        max_json_bytes: int = DEFAULT_MAX_JSON_BYTES,
        max_total_uncompressed_bytes: int = DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
    ) -> None:
        self.archive_path = archive_path.resolve()
        self.max_archive_bytes = max_archive_bytes
        self.max_member_count = max_member_count
        self.max_json_bytes = max_json_bytes
        self.max_total_uncompressed_bytes = max_total_uncompressed_bytes

    def discover_sessions(self) -> ChatGPTSourceDiscovery:
        self._validate_archive_file()
        warnings: list[ChatGPTSourceWarning] = []
        sessions: list[ChatGPTSessionReference] = []
        seen_session_ids: set[str] = set()
        try:
            with zipfile.ZipFile(self.archive_path) as archive:
                conversation_members = self._validated_members(archive)
                if not conversation_members:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_CONVERSATIONS_MISSING",
                        "ChatGPT export does not contain a conversations JSON file",
                    )
                for member in conversation_members:
                    records = self._read_records(archive, member, warnings)
                    for index, record in records:
                        session_id = self._session_id(record)
                        if session_id is None:
                            warnings.append(
                                ChatGPTSourceWarning(
                                    "CHATGPT_EXPORT_SESSION_ID_MISSING",
                                    member.filename,
                                    index,
                                )
                            )
                            continue
                        if session_id in seen_session_ids:
                            warnings.append(
                                ChatGPTSourceWarning(
                                    "CHATGPT_EXPORT_SESSION_ID_DUPLICATE",
                                    member.filename,
                                    index,
                                )
                            )
                            continue
                        sessions.append(
                            ChatGPTSessionReference(
                                source_session_id=session_id,
                                title=self._title(record),
                                source_member=member.filename,
                                source_index=index,
                            )
                        )
                        seen_session_ids.add(session_id)
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_INVALID_ZIP", "ChatGPT export is not a valid ZIP file"
            ) from error
        return ChatGPTSourceDiscovery(
            archive_path=self.archive_path,
            archive_sha256=self._archive_hash(),
            sessions=tuple(sessions),
            warnings=tuple(warnings),
        )

    def read_session(self, session_ref: ChatGPTSessionReference) -> dict[str, Any]:
        if not self.supports(session_ref):
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_SESSION_REF_UNSUPPORTED",
                "Session reference is not supported by this source",
            )
        self._validate_archive_file()
        try:
            with zipfile.ZipFile(self.archive_path) as archive:
                members = {
                    member.filename: member
                    for member in self._validated_members(archive)
                }
                member = members.get(session_ref.source_member)
                if member is None:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_SESSION_MEMBER_MISSING",
                        "Referenced conversations file is missing",
                    )
                warnings: list[ChatGPTSourceWarning] = []
                records = self._read_records(archive, member, warnings)
                if warnings:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_SESSION_MEMBER_INVALID",
                        "Referenced conversations file is invalid",
                    )
                record = next(
                    (
                        value
                        for index, value in records
                        if index == session_ref.source_index
                    ),
                    None,
                )
                if record is None:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_SESSION_INDEX_INVALID",
                        "Referenced conversation index is invalid",
                    )
                if self._session_id(record) != session_ref.source_session_id:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_SESSION_ID_CHANGED",
                        "Referenced conversation no longer matches its source id",
                    )
                return dict(record)
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as error:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_INVALID_ZIP", "ChatGPT export is not a valid ZIP file"
            ) from error

    @staticmethod
    def supports(session_ref: ChatGPTSessionReference) -> bool:
        return session_ref.source_format == "chatgpt_export"

    def _validate_archive_file(self) -> None:
        if not self.archive_path.is_file():
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_NOT_FOUND", "ChatGPT export ZIP was not found"
            )
        try:
            size = self.archive_path.stat().st_size
        except OSError as error:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_UNREADABLE", "ChatGPT export ZIP cannot be read"
            ) from error
        if size > self.max_archive_bytes:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_TOO_LARGE", "ChatGPT export ZIP exceeds the size limit"
            )

    def _validated_members(self, archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
        members = archive.infolist()
        if len(members) > self.max_member_count:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_TOO_MANY_MEMBERS",
                "ChatGPT export ZIP contains too many members",
            )
        total_uncompressed = 0
        conversation_members: list[zipfile.ZipInfo] = []
        seen_member_paths: set[str] = set()
        for member in members:
            self._validate_member_path(member.filename)
            member_key = member.filename.replace("\\", "/").casefold()
            if member_key in seen_member_paths:
                raise ChatGPTSessionSourceError(
                    "CHATGPT_EXPORT_MEMBER_DUPLICATE",
                    "ChatGPT export contains a duplicate member path",
                )
            seen_member_paths.add(member_key)
            if member.flag_bits & 0x1:
                raise ChatGPTSessionSourceError(
                    "CHATGPT_EXPORT_ENCRYPTED_MEMBER",
                    "Encrypted ChatGPT export members are not supported",
                )
            total_uncompressed += member.file_size
            if total_uncompressed > self.max_total_uncompressed_bytes:
                raise ChatGPTSessionSourceError(
                    "CHATGPT_EXPORT_UNCOMPRESSED_TOO_LARGE",
                    "ChatGPT export exceeds the uncompressed size limit",
                )
            if CONVERSATION_FILE_PATTERN.fullmatch(
                PurePosixPath(member.filename.replace("\\", "/")).name
            ):
                if member.file_size > self.max_json_bytes:
                    raise ChatGPTSessionSourceError(
                        "CHATGPT_EXPORT_CONVERSATIONS_TOO_LARGE",
                        "ChatGPT conversations JSON exceeds the size limit",
                    )
                conversation_members.append(member)
        return sorted(conversation_members, key=lambda item: item.filename.casefold())

    @staticmethod
    def _validate_member_path(filename: str) -> None:
        normalized = filename.replace("\\", "/")
        path = PurePosixPath(normalized)
        if (
            not normalized
            or normalized.startswith("/")
            or re.match(r"^[A-Za-z]:", normalized)
            or ".." in path.parts
        ):
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_UNSAFE_MEMBER_PATH",
                "ChatGPT export contains an unsafe member path",
            )

    @staticmethod
    def _read_records(
        archive: zipfile.ZipFile,
        member: zipfile.ZipInfo,
        warnings: list[ChatGPTSourceWarning],
    ) -> list[tuple[int, Mapping[str, Any]]]:
        try:
            content = archive.read(member)
            decoded = content.decode("utf-8-sig")
            payload = json.loads(decoded)
        except (OSError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
            warnings.append(
                ChatGPTSourceWarning(
                    "CHATGPT_EXPORT_CONVERSATIONS_INVALID", member.filename
                )
            )
            return []
        if not isinstance(payload, list):
            warnings.append(
                ChatGPTSourceWarning(
                    "CHATGPT_EXPORT_CONVERSATIONS_NOT_LIST", member.filename
                )
            )
            return []
        records: list[tuple[int, Mapping[str, Any]]] = []
        for index, value in enumerate(payload):
            if isinstance(value, Mapping):
                records.append((index, value))
            else:
                warnings.append(
                    ChatGPTSourceWarning(
                        "CHATGPT_EXPORT_SESSION_RECORD_INVALID", member.filename, index
                    )
                )
        return records

    @staticmethod
    def _session_id(record: Mapping[str, Any]) -> str | None:
        value = record.get("id") or record.get("conversation_id")
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _title(record: Mapping[str, Any]) -> str | None:
        value = record.get("title")
        return value if isinstance(value, str) and value else None

    def _archive_hash(self) -> str:
        digest = hashlib.sha256()
        try:
            with self.archive_path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise ChatGPTSessionSourceError(
                "CHATGPT_EXPORT_UNREADABLE", "ChatGPT export ZIP cannot be read"
            ) from error
        return digest.hexdigest()
