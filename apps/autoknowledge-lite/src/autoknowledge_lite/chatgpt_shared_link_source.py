"""Read-only discovery of a ChatGPT session in an explicit shared-link snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from autoknowledge_lite.chatgpt_session_source import (
    ChatGPTSessionReference,
    ChatGPTSourceDiscovery,
    ChatGPTSourceWarning,
)

DEFAULT_MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024
MAX_DECODE_DEPTH = 3
MAX_TRAVERSED_VALUES = 100_000
SHARE_PATH_PATTERN = re.compile(r"^/share/([A-Za-z0-9_-]{8,128})/?$")
JSON_STRING_PATTERN = re.compile(r'"(?:[^"\\]|\\.)*"')
REFERENCE_KEY_PATTERN = re.compile(r"^_(\d+)$")
COPIED_URL_IGNORABLES = str.maketrans("", "", "\u200b\u200c\u200d\u2060\ufeff")


class ChatGPTSharedLinkSourceError(RuntimeError):
    """Raised when a shared-link snapshot cannot be trusted or interpreted."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ChatGPTSharedLinkSource:
    """Project only structured data actually present in a local link snapshot."""

    source_type = "chatgpt"

    def __init__(
        self,
        shared_url: str,
        snapshot_path: Path,
        *,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        self.shared_url = canonical_chatgpt_shared_url(shared_url)
        self.snapshot_path = snapshot_path.resolve()
        self.max_snapshot_bytes = max_snapshot_bytes
        self.share_id = chatgpt_share_id(self.shared_url)

    def discover_sessions(self) -> ChatGPTSourceDiscovery:
        records = self._records()
        selected, warnings = self._select_record(records)
        session_id = self._session_id(selected)
        if session_id is None:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SESSION_ID_MISSING",
                "Shared snapshot does not contain a conversation id",
            )
        reference = ChatGPTSessionReference(
            source_session_id=session_id,
            title=self._optional_text(selected.get("title")),
            source_member=f"chatgpt-share:{self.share_id}",
            source_index=0,
            source_format="chatgpt_shared_link",
        )
        return ChatGPTSourceDiscovery(
            archive_path=self.snapshot_path,
            archive_sha256=self._snapshot_hash(),
            sessions=(reference,),
            warnings=warnings,
        )

    def read_session(self, session_ref: ChatGPTSessionReference) -> dict[str, Any]:
        if not self.supports(session_ref):
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SESSION_REF_UNSUPPORTED",
                "Session reference is not supported by this shared-link source",
            )
        selected, _ = self._select_record(self._records())
        if self._session_id(selected) != session_ref.source_session_id:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SESSION_CHANGED",
                "Shared snapshot content changed after discovery",
            )
        return dict(selected)

    def supports(self, session_ref: ChatGPTSessionReference) -> bool:
        return (
            session_ref.source_format == "chatgpt_shared_link"
            and session_ref.source_member == f"chatgpt-share:{self.share_id}"
            and session_ref.source_index == 0
        )

    def _records(self) -> tuple[Mapping[str, Any], ...]:
        snapshot = self._read_snapshot()
        decoded = list(self._decoded_values(snapshot))
        records: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        seen_containers: set[int] = set()
        traversed = 0
        pending: list[Any] = decoded[:]
        while pending:
            value = pending.pop()
            if isinstance(value, Mapping) or (
                isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            ):
                container_id = id(value)
                if container_id in seen_containers:
                    continue
                seen_containers.add(container_id)
            traversed += 1
            if traversed > MAX_TRAVERSED_VALUES:
                raise ChatGPTSharedLinkSourceError(
                    "CHATGPT_SHARED_SNAPSHOT_TOO_COMPLEX",
                    "Shared snapshot contains too many structured values",
                )
            if isinstance(value, Mapping):
                if self._looks_like_conversation(value):
                    canonical = json.dumps(
                        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                    )
                    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    if digest not in seen:
                        records.append(value)
                        seen.add(digest)
                pending.extend(value.values())
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                pending.extend(value)
        if not records:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_CONVERSATION_MISSING",
                "Shared snapshot does not contain structured conversation data",
            )
        return tuple(records)

    def _decoded_values(self, snapshot: str) -> Iterator[Any]:
        pending = [snapshot]
        seen: set[str] = set()
        for _ in range(MAX_DECODE_DEPTH):
            next_pending: list[str] = []
            for source in pending:
                stripped = source.strip()
                if stripped and stripped not in seen:
                    seen.add(stripped)
                    try:
                        decoded = json.loads(stripped)
                    except json.JSONDecodeError:
                        decoded = None
                    if decoded is not None:
                        yield decoded
                        referenced = _decode_reference_table(decoded)
                        if referenced is not None:
                            yield referenced
                for token in JSON_STRING_PATTERN.findall(source):
                    try:
                        value = json.loads(token)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, str) and value.strip() not in seen:
                        next_pending.append(value)
            pending = next_pending

    def _select_record(
        self, records: tuple[Mapping[str, Any], ...]
    ) -> tuple[Mapping[str, Any], tuple[ChatGPTSourceWarning, ...]]:
        matches = [
            record for record in records if self._session_id(record) == self.share_id
        ]
        candidates = matches or list(records)
        selected = max(candidates, key=self._message_count)
        warnings: tuple[ChatGPTSourceWarning, ...] = ()
        if len(records) > 1:
            warnings = (
                ChatGPTSourceWarning(
                    "CHATGPT_SHARED_MULTIPLE_CONVERSATIONS",
                    f"chatgpt-share:{self.share_id}",
                    0,
                ),
            )
        return selected, warnings

    def _read_snapshot(self) -> str:
        try:
            size = self.snapshot_path.stat().st_size
        except OSError as error:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SNAPSHOT_UNREADABLE",
                "Shared snapshot cannot be read",
            ) from error
        if size > self.max_snapshot_bytes:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SNAPSHOT_TOO_LARGE",
                "Shared snapshot exceeds the size limit",
            )
        try:
            return self.snapshot_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SNAPSHOT_UNREADABLE",
                "Shared snapshot must be readable UTF-8 text",
            ) from error

    def _snapshot_hash(self) -> str:
        digest = hashlib.sha256()
        try:
            with self.snapshot_path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as error:
            raise ChatGPTSharedLinkSourceError(
                "CHATGPT_SHARED_SNAPSHOT_UNREADABLE",
                "Shared snapshot cannot be hashed",
            ) from error
        return digest.hexdigest()

    @staticmethod
    def _looks_like_conversation(value: Mapping[str, Any]) -> bool:
        mapping = value.get("mapping")
        messages = value.get("messages")
        return isinstance(mapping, Mapping) or (
            isinstance(messages, Sequence) and not isinstance(messages, (str, bytes))
        )

    @staticmethod
    def _session_id(value: Mapping[str, Any]) -> str | None:
        return ChatGPTSharedLinkSource._optional_text(
            value.get("id") or value.get("conversation_id")
        )

    @staticmethod
    def _message_count(value: Mapping[str, Any]) -> int:
        mapping = value.get("mapping")
        if isinstance(mapping, Mapping):
            return len(mapping)
        messages = value.get("messages")
        if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes)):
            return len(messages)
        return 0

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None


def chatgpt_share_id(url: str) -> str:
    """Validate a public ChatGPT shared-link URL and return its source id."""

    canonical_url = canonical_chatgpt_shared_url(url)
    match = SHARE_PATH_PATTERN.fullmatch(urlsplit(canonical_url).path)
    assert match is not None
    return match.group(1)


def canonical_chatgpt_shared_url(url: str) -> str:
    """Normalize safe copy artifacts without weakening share-host validation."""

    value = url.translate(COPIED_URL_IGNORABLES).strip()
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as error:
        raise ChatGPTSharedLinkSourceError(
            "CHATGPT_SHARED_URL_INVALID",
            "Shared link contains an invalid port",
        ) from error
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold() != "chatgpt.com"
        or port not in {None, 443}
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ChatGPTSharedLinkSourceError(
            "CHATGPT_SHARED_URL_INVALID",
            "Shared link must be an HTTPS chatgpt.com URL without credentials",
        )
    match = SHARE_PATH_PATTERN.fullmatch(parsed.path)
    if not match:
        raise ChatGPTSharedLinkSourceError(
            "CHATGPT_SHARED_URL_INVALID",
            "Shared link must use /share/<conversation-ID>",
        )
    return f"https://chatgpt.com/share/{match.group(1)}"


def _decode_reference_table(value: Any) -> Any | None:
    """Decode ChatGPT's streamed loader reference table when one is present."""

    if (
        not isinstance(value, list)
        or not value
        or len(value) > MAX_TRAVERSED_VALUES
        or not isinstance(value[0], Mapping)
        or not value[0]
        or not all(
            isinstance(key, str) and REFERENCE_KEY_PATTERN.fullmatch(key)
            for key in value[0]
        )
    ):
        return None

    memo: dict[int, Any] = {}

    def resolve(reference: int) -> Any:
        if reference < 0:
            return None
        if reference >= len(value):
            raise ValueError("reference is outside the streamed loader table")
        if reference in memo:
            return memo[reference]

        item = value[reference]
        if isinstance(item, Mapping):
            decoded: dict[str, Any] = {}
            memo[reference] = decoded
            for encoded_key, encoded_value in item.items():
                match = REFERENCE_KEY_PATTERN.fullmatch(encoded_key)
                if match is None:
                    raise ValueError("streamed loader object is malformed")
                key = resolve(int(match.group(1)))
                if not isinstance(key, str):
                    raise ValueError("streamed loader object key is not text")
                decoded[key] = (
                    resolve(encoded_value)
                    if type(encoded_value) is int
                    else encoded_value
                )
            return decoded
        if isinstance(item, list):
            decoded_list: list[Any] = []
            memo[reference] = decoded_list
            for encoded_value in item:
                decoded_list.append(
                    resolve(encoded_value)
                    if type(encoded_value) is int
                    else encoded_value
                )
            return decoded_list

        memo[reference] = item
        return item

    try:
        return resolve(0)
    except (RecursionError, ValueError):
        return None
