from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from mde.codex_capture.security import is_sensitive_path, redact_text

ADAPTER_VERSION = "1.0.0"
MAX_MESSAGE_BYTES = 256 * 1024
MESSAGE_EDGE_BYTES = 96 * 1024
VALID_ROLES = {"user", "assistant", "tool", "system_summary", "unknown"}


class CodexSessionAdapterError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SessionCheckpoint:
    source_session_id: str
    source_fingerprint: str
    last_message_sequence: int
    last_event_id: str | None = None


class CodexSessionSource(Protocol):
    source_type: str

    def discover_sessions(self) -> list[dict[str, Any]]: ...

    def read_session(
        self,
        session_ref: dict[str, Any],
        checkpoint: SessionCheckpoint | None,
    ) -> dict[str, Any]: ...

    def supports(self, session_ref: dict[str, Any]) -> bool: ...


class AppServerClient:
    """Small client for the official Codex app-server stdio JSON-RPC API."""

    def __init__(self, executable: str | None = None, timeout: float = 15.0) -> None:
        self.executable = (
            executable
            or os.environ.get("MDE_CODEX_EXECUTABLE")
            or shutil.which("codex")
        )
        self.timeout = timeout

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.executable:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_SOURCE_NOT_FOUND", "Codex executable is not configured"
            )
        try:
            process = subprocess.Popen(
                [self.executable, "app-server"],
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
            )
        except PermissionError as error:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_ACCESS_DENIED", "Codex app-server cannot be executed"
            ) from error
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_DISCOVERY_FAILED", "Codex app-server did not respond"
            ) from error
        if process.stdin is None or process.stdout is None:
            process.terminate()
            raise CodexSessionAdapterError(
                "CODEX_SESSION_DISCOVERY_FAILED",
                "Codex app-server pipes are unavailable",
            )
        responses: queue.Queue[str | None] = queue.Queue()

        def read_stdout() -> None:
            try:
                for line in process.stdout:
                    responses.put(line)
            finally:
                responses.put(None)

        reader = threading.Thread(target=read_stdout, daemon=True)
        reader.start()
        deadline = time.monotonic() + self.timeout
        try:
            self._send(
                process,
                {
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "clientInfo": {
                            "name": "mde_autoknowledge",
                            "title": "MDE AutoKnowledge",
                            "version": ADAPTER_VERSION,
                        }
                    },
                },
            )
            self._wait_response(responses, 1, deadline)
            self._send(process, {"method": "initialized", "params": {}})
            self._send(process, {"method": method, "id": 2, "params": params})
            return self._wait_response(responses, 2, deadline)
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

    @staticmethod
    def _send(process: subprocess.Popen[str], message: dict[str, Any]) -> None:
        if process.stdin is None:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_DISCOVERY_FAILED", "Codex app-server stdin closed"
            )
        process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()

    @staticmethod
    def _wait_response(
        responses: queue.Queue[str | None], request_id: int, deadline: float
    ) -> dict[str, Any]:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CodexSessionAdapterError(
                    "CODEX_SESSION_DISCOVERY_FAILED", "Codex app-server timed out"
                )
            try:
                line = responses.get(timeout=remaining)
            except queue.Empty as error:
                raise CodexSessionAdapterError(
                    "CODEX_SESSION_DISCOVERY_FAILED", "Codex app-server timed out"
                ) from error
            if line is None:
                raise CodexSessionAdapterError(
                    "CODEX_SESSION_DISCOVERY_FAILED",
                    "Codex app-server closed before responding",
                )
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                continue
            if response.get("id") == request_id:
                if "error" in response:
                    raise CodexSessionAdapterError(
                        "CODEX_SESSION_DISCOVERY_FAILED",
                        str(
                            response["error"].get(
                                "message", "app-server request failed"
                            )
                        ),
                    )
                return dict(response.get("result") or {})


class CodexAppSessionAdapter:
    source_type = "codex_app_server"

    def __init__(self, client: AppServerClient | None = None) -> None:
        self.client = client or AppServerClient()

    def discover_sessions(self) -> list[dict[str, Any]]:
        result = self.client.request(
            "thread/list",
            {
                "limit": 100,
                "sortKey": "updated_at",
                "sortDirection": "desc",
                "sourceKinds": ["cli", "vscode", "appServer"],
            },
        )
        return [self._reference(item) for item in result.get("data", [])]

    def read_session(
        self,
        session_ref: dict[str, Any],
        checkpoint: SessionCheckpoint | None,
    ) -> dict[str, Any]:
        source_id = str(session_ref.get("sourceSessionId") or "")
        if not source_id:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_FORMAT_UNSUPPORTED", "sourceSessionId is required"
            )
        result = self.client.request(
            "thread/read", {"threadId": source_id, "includeTurns": True}
        )
        thread = result.get("thread")
        if not isinstance(thread, dict):
            raise CodexSessionAdapterError(
                "CODEX_SESSION_FORMAT_UNSUPPORTED", "thread/read response has no thread"
            )
        return normalize_thread(thread, checkpoint=checkpoint)

    def supports(self, session_ref: dict[str, Any]) -> bool:
        return session_ref.get("clientType") in {
            "codex_app_server",
            "codex_app",
            "codex_cli",
            "codex_ide",
        }

    @staticmethod
    def _reference(thread: dict[str, Any]) -> dict[str, Any]:
        raw_title = str(thread.get("name") or thread.get("preview") or "")
        title = _normalize_content(raw_title).replace("\n", " ")[:160] or None
        return {
            "sourceSessionId": str(thread.get("id", "")),
            "sourceRootSessionId": thread.get("sessionId"),
            "clientType": "codex_app_server",
            "title": title,
            "createdAt": thread.get("createdAt"),
            "updatedAt": thread.get("updatedAt"),
            "projectPathAlias": None,
            "_sourceCwd": thread.get("cwd"),
            "status": (
                (thread.get("status") or {}).get("type", "unknown")
                if isinstance(thread.get("status"), dict)
                else "unknown"
            ),
            "adapterName": "CodexAppSessionAdapter",
            "adapterVersion": ADAPTER_VERSION,
            "sourceFormatVersion": "app-server-v2",
        }


class ManualImportSessionAdapter:
    source_type = "manual_import"

    def discover_sessions(self) -> list[dict[str, Any]]:
        return []

    def supports(self, session_ref: dict[str, Any]) -> bool:
        return bool(session_ref.get("importPath"))

    def read_session(
        self,
        session_ref: dict[str, Any],
        checkpoint: SessionCheckpoint | None,
    ) -> dict[str, Any]:
        source = Path(str(session_ref.get("importPath", "")))
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_SOURCE_NOT_FOUND", source.name
            ) from error
        except (OSError, json.JSONDecodeError) as error:
            raise CodexSessionAdapterError(
                "CODEX_SESSION_PARSE_FAILED", source.name
            ) from error
        thread = document.get("thread") if isinstance(document, dict) else None
        if not isinstance(thread, dict) and isinstance(document, dict):
            thread = (document.get("result") or {}).get("thread")
        if not isinstance(thread, dict):
            raise CodexSessionAdapterError(
                "CODEX_SESSION_FORMAT_UNSUPPORTED",
                "Import must be an official thread/read JSON response",
            )
        result = normalize_thread(thread, checkpoint=checkpoint)
        result["adapter"] = {
            "adapterName": "ManualImportSessionAdapter",
            "adapterVersion": ADAPTER_VERSION,
            "sourceFormatVersion": "app-server-v2-export",
        }
        return result


class CodexCliSessionAdapter(CodexAppSessionAdapter):
    """CLI threads are exposed through the same official app-server contract."""


class CodexIdeSessionAdapter(CodexAppSessionAdapter):
    """IDE threads are exposed through the same official app-server contract."""


def normalize_thread(
    thread: dict[str, Any], *, checkpoint: SessionCheckpoint | None = None
) -> dict[str, Any]:
    source_id = str(thread.get("id") or "")
    if not source_id:
        raise CodexSessionAdapterError(
            "CODEX_SESSION_FORMAT_UNSUPPORTED", "Thread id is missing"
        )
    messages: list[dict[str, Any]] = []
    warnings: list[str] = []
    failed = 0
    for turn_index, turn in enumerate(thread.get("turns") or []):
        if not isinstance(turn, dict):
            failed += 1
            warnings.append("UNKNOWN_TURN_TYPE")
            continue
        created_at = turn.get("createdAt") or turn.get("startedAt")
        for item_index, item in enumerate(turn.get("items") or []):
            if not isinstance(item, dict):
                failed += 1
                warnings.append("UNKNOWN_EVENT_TYPE")
                continue
            normalized = normalize_item(
                item,
                created_at=item.get("createdAt") or created_at,
                ordinal=(turn_index, item_index),
            )
            if normalized is None:  # Deliberately excludes private reasoning.
                continue
            if normalized["role"] == "unknown":
                failed += 1
                warnings.append("CODEX_MESSAGE_ROLE_UNKNOWN")
            messages.append(normalized)
        turn_error = turn.get("error")
        if turn_error:
            normalized_error = normalize_item(
                {
                    "type": "error",
                    "id": f"{turn.get('id', turn_index)}-error",
                    "error": turn_error,
                },
                created_at=created_at,
                ordinal=(turn_index, len(turn.get("items") or [])),
            )
            if normalized_error:
                messages.append(normalized_error)
    messages = deduplicate_messages(messages)
    for sequence, message in enumerate(messages, 1):
        message["sequence"] = sequence
    fingerprint = hashlib.sha256(
        "\n".join(item["contentHash"] for item in messages).encode("utf-8")
    ).hexdigest()
    previous = (
        checkpoint.last_message_sequence
        if checkpoint and checkpoint.source_session_id == source_id
        else 0
    )
    checkpoint_invalid = bool(
        checkpoint
        and checkpoint.source_session_id == source_id
        and (
            previous > len(messages)
            or (
                previous == len(messages)
                and checkpoint.source_fingerprint
                and checkpoint.source_fingerprint != fingerprint
            )
        )
    )
    if checkpoint_invalid:
        warnings.append("CODEX_SESSION_CHECKPOINT_INVALID")
    new_messages = messages if checkpoint_invalid else messages[previous:]
    return {
        "sourceSessionId": source_id,
        "sourceRootSessionId": thread.get("sessionId"),
        "title": thread.get("name") or thread.get("preview"),
        "createdAt": thread.get("createdAt"),
        "updatedAt": thread.get("updatedAt"),
        "messages": messages,
        "newMessages": new_messages,
        "parseStatus": "partial" if failed else "complete",
        "parsedMessages": len(messages),
        "failedEvents": failed,
        "warnings": sorted(set(warnings)),
        "checkpoint": {
            "sourceSessionId": source_id,
            "sourceFingerprint": fingerprint,
            "lastMessageSequence": len(messages),
            "lastEventId": messages[-1].get("sourceMessageId") if messages else None,
        },
        "adapter": {
            "adapterName": "CodexAppSessionAdapter",
            "adapterVersion": ADAPTER_VERSION,
            "sourceFormatVersion": "app-server-v2",
        },
    }


def normalize_item(
    item: dict[str, Any], *, created_at: Any, ordinal: tuple[int, int]
) -> dict[str, Any] | None:
    item_type = str(item.get("type") or "unknown")
    if item_type == "reasoning":
        return None
    role, message_type, content = "unknown", "unknown", ""
    metadata: dict[str, Any] = {
        "clientType": "codex_app_server",
        "sourceItemType": item_type,
    }
    if item_type == "userMessage":
        role, message_type = "user", "text"
        content = "\n".join(
            str(part.get("text", ""))
            for part in item.get("content") or []
            if isinstance(part, dict) and part.get("type") == "text"
        )
    elif item_type == "agentMessage":
        role = "assistant"
        message_type = "progress" if item.get("phase") == "commentary" else "text"
        content = str(item.get("text") or "")
        metadata["phase"] = item.get("phase")
    elif item_type == "plan":
        role, message_type, content = (
            "assistant",
            "progress",
            str(item.get("text") or ""),
        )
    elif item_type == "commandExecution":
        role, message_type, content = "tool", "command", str(item.get("command") or "")
        output = item.get("aggregatedOutput")
        if output:
            content += "\n\n" + str(output)
            metadata["hasCommandResult"] = True
        metadata.update(
            {
                key: item.get(key)
                for key in ("cwd", "status", "exitCode", "durationMs")
                if item.get(key) is not None
            }
        )
    elif item_type == "fileChange":
        role, message_type = "tool", "patch"
        safe_changes = [
            change
            for change in item.get("changes") or []
            if isinstance(change, dict)
            and change.get("path")
            and not is_sensitive_path(str(change["path"]))
        ]
        content = "\n\n".join(str(change.get("diff") or "") for change in safe_changes)
        metadata["patchType"] = "codex_displayed_patch"
        metadata["appliedState"] = "unknown"
        metadata["status"] = item.get("status")
        metadata["changes"] = [
            {
                key: change.get(key)
                for key in ("path", "kind", "diff", "oldPath")
                if change.get(key) is not None
            }
            for change in safe_changes
        ]
        omitted = len(item.get("changes") or []) - len(safe_changes)
        if omitted:
            metadata["sensitiveChangesOmitted"] = omitted
    elif item_type in {
        "mcpToolCall",
        "dynamicToolCall",
        "collabToolCall",
        "webSearch",
        "imageView",
    }:
        role, message_type = "tool", "progress"
        content = str(item.get("tool") or item.get("query") or item_type)
        metadata["status"] = item.get("status")
    elif item_type in {"enteredReviewMode", "exitedReviewMode"}:
        role, message_type, content = (
            "assistant",
            "progress",
            str(item.get("review") or item_type),
        )
    elif item_type == "contextCompaction":
        role, message_type, content = (
            "system_summary",
            "progress",
            "Codex conversation context was compacted.",
        )
    elif item_type == "error":
        role, message_type = "tool", "error"
        error = item.get("error") or {}
        content = str(error.get("message") if isinstance(error, dict) else error)
    else:
        content = str(item.get("text") or item.get("message") or item_type)
    content = _normalize_content(content)
    content, truncated, original_bytes = _truncate(content)
    source_id = str(item.get("id") or "") or None
    created = _normalize_time(created_at)
    digest_input = "\0".join((role, message_type, content, created or ""))
    content_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    if not source_id:
        source_id = f"generated-{ordinal[0]}-{ordinal[1]}-{content_hash[:12]}"
    metadata["truncated"] = truncated
    metadata["originalByteLength"] = original_bytes
    metadata = _sanitize_value(metadata)
    return {
        "messageId": f"msg_{content_hash[:24]}",
        "sourceMessageId": source_id,
        "sequence": 0,
        "role": role if role in VALID_ROLES else "unknown",
        "messageType": message_type,
        "content": content,
        "contentHash": content_hash,
        "createdAt": created,
        "metadata": metadata,
    }


def deduplicate_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_source: set[str] = set()
    seen_hash: set[str] = set()
    result: list[dict[str, Any]] = []
    for message in messages:
        source_id = str(message.get("sourceMessageId") or "")
        digest = str(message.get("contentHash") or "")
        if (source_id and source_id in seen_source) or digest in seen_hash:
            continue
        if source_id:
            seen_source.add(source_id)
        seen_hash.add(digest)
        result.append(message)
    return result


def _normalize_content(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "".join(
        character
        for character in normalized
        if character in "\n\t" or ord(character) >= 32
    ).strip()
    profile = os.environ.get("USERPROFILE")
    if profile:
        normalized = normalized.replace(profile, "%USERPROFILE%").replace(
            profile.replace("\\", "/"), "%USERPROFILE%"
        )
    return redact_text(normalized)[0]


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _normalize_content(value)
    if isinstance(value, dict):
        return {key: _sanitize_value(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


def _truncate(value: str) -> tuple[str, bool, int]:
    raw = value.encode("utf-8")
    if len(raw) <= MAX_MESSAGE_BYTES:
        return value, False, len(raw)
    prefix = raw[:MESSAGE_EDGE_BYTES].decode("utf-8", "ignore")
    suffix = raw[-MESSAGE_EDGE_BYTES:].decode("utf-8", "ignore")
    return prefix + "\n...[TRUNCATED]...\n" + suffix, True, len(raw)


def _normalize_time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        from datetime import datetime, timezone

        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return str(value)


def checkpoint_from_dict(value: dict[str, Any]) -> SessionCheckpoint | None:
    try:
        return SessionCheckpoint(
            source_session_id=str(value["sourceSessionId"]),
            source_fingerprint=str(value.get("sourceFingerprint", "")),
            last_message_sequence=int(value.get("lastMessageSequence", 0)),
            last_event_id=value.get("lastEventId"),
        )
    except (KeyError, TypeError, ValueError):
        return None
