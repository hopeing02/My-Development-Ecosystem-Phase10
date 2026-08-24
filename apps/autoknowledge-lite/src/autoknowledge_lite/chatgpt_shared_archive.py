"""Explicit network retrieval and immutable local storage of shared snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from autoknowledge_lite.chatgpt_shared_link_source import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    ChatGPTSharedLinkSourceError,
    canonical_chatgpt_shared_url,
    chatgpt_share_id,
)

MAX_REDIRECTS = 3


class ChatGPTSharedFetchError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ChatGPTSharedArchiveError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ChatGPTSharedSnapshot:
    shared_url: str
    share_id: str
    content: bytes
    content_type: str
    snapshot_sha256: str


class ChatGPTSharedSnapshotFetcher:
    """Fetch one explicitly submitted public share URL without cookies or auth."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        self.client = client or httpx.Client(
            timeout=20,
            follow_redirects=False,
            headers={"User-Agent": "AutoKnowledge-Lite/0.2"},
        )
        self.max_snapshot_bytes = max_snapshot_bytes

    def fetch(self, shared_url: str) -> ChatGPTSharedSnapshot:
        canonical_url = self._canonical_url(shared_url)
        share_id = self._validated_id(canonical_url)
        current_url = canonical_url
        for _ in range(MAX_REDIRECTS + 1):
            current_url = self._canonical_url(current_url)
            if self._validated_id(current_url) != share_id:
                raise ChatGPTSharedFetchError(
                    "CHATGPT_SHARED_REDIRECT_REJECTED",
                    "Shared link redirected to a different conversation",
                )
            try:
                with self.client.stream("GET", current_url) as response:
                    location = self._redirect(response)
                    if location is not None:
                        current_url = urljoin(current_url, location)
                        continue
                    content_type = self._validated_content_type(response)
                    content = self._read_limited(response)
            except httpx.HTTPError as error:
                raise ChatGPTSharedFetchError(
                    "CHATGPT_SHARED_FETCH_FAILED",
                    "ChatGPT shared link could not be retrieved",
                ) from error
            return ChatGPTSharedSnapshot(
                shared_url=canonical_url,
                share_id=share_id,
                content=content,
                content_type=content_type,
                snapshot_sha256=hashlib.sha256(content).hexdigest(),
            )
        raise ChatGPTSharedFetchError(
            "CHATGPT_SHARED_REDIRECT_LIMIT",
            "ChatGPT shared link redirected too many times",
        )

    @staticmethod
    def _redirect(response: httpx.Response) -> str | None:
        if not response.is_redirect:
            return None
        location = response.headers.get("location")
        if not location:
            raise ChatGPTSharedFetchError(
                "CHATGPT_SHARED_REDIRECT_INVALID",
                "ChatGPT shared link returned an invalid redirect",
            )
        return location

    def _validated_content_type(self, response: httpx.Response) -> str:
        if not response.is_success:
            raise ChatGPTSharedFetchError(
                "CHATGPT_SHARED_FETCH_HTTP_ERROR",
                "ChatGPT shared link returned an error response",
            )
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if content_type not in {"text/html", "application/json"}:
            raise ChatGPTSharedFetchError(
                "CHATGPT_SHARED_CONTENT_TYPE_UNSUPPORTED",
                "ChatGPT shared link did not return HTML or JSON",
            )
        content_length = response.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > self.max_snapshot_bytes:
            raise ChatGPTSharedFetchError(
                "CHATGPT_SHARED_SNAPSHOT_TOO_LARGE",
                "ChatGPT shared snapshot exceeds the size limit",
            )
        return content_type

    def _read_limited(self, response: httpx.Response) -> bytes:
        content = bytearray()
        for chunk in response.iter_bytes():
            content.extend(chunk)
            if len(content) > self.max_snapshot_bytes:
                raise ChatGPTSharedFetchError(
                    "CHATGPT_SHARED_SNAPSHOT_TOO_LARGE",
                    "ChatGPT shared snapshot exceeds the size limit",
                )
        return bytes(content)

    @staticmethod
    def _validated_id(url: str) -> str:
        try:
            return chatgpt_share_id(url)
        except ChatGPTSharedLinkSourceError as error:
            raise ChatGPTSharedFetchError(error.code, str(error)) from error

    @staticmethod
    def _canonical_url(url: str) -> str:
        try:
            return canonical_chatgpt_shared_url(url)
        except ChatGPTSharedLinkSourceError as error:
            raise ChatGPTSharedFetchError(error.code, str(error)) from error


class ChatGPTSharedSnapshotManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    import_id: str = Field(min_length=1)
    source_type: Literal["chatgpt"] = "chatgpt"
    acquisition_method: Literal["shared_link"] = "shared_link"
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_size: int = Field(ge=0)
    share_id_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_type: Literal["text/html", "application/json"]
    acquired_at: datetime

    @field_validator("acquired_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("acquired_at must include a timezone")
        return value


class ChatGPTSharedArchiveResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    import_id: str
    snapshot_path: Path
    manifest_path: Path
    duplicate: bool
    manifest: ChatGPTSharedSnapshotManifest


class ChatGPTSharedSnapshotStore:
    """Persist immutable shared snapshots in Git-ignored local data."""

    def __init__(
        self,
        data_dir: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.data_dir = data_dir.resolve()
        self.imports_dir = self.data_dir / "raw" / "chatgpt" / "shared"
        self.clock = clock or (lambda: datetime.now(UTC))
        self._lock = Lock()

    def archive(self, snapshot: ChatGPTSharedSnapshot) -> ChatGPTSharedArchiveResult:
        actual_hash = hashlib.sha256(snapshot.content).hexdigest()
        if actual_hash != snapshot.snapshot_sha256:
            raise ChatGPTSharedArchiveError(
                "CHATGPT_SHARED_SNAPSHOT_HASH_MISMATCH",
                "Shared snapshot content does not match its hash",
            )
        import_id = f"chatgpt_shared_{actual_hash[:24]}"
        destination = self.imports_dir / import_id
        snapshot_path = destination / "snapshot.html"
        manifest_path = destination / "manifest.json"
        with self._lock:
            if destination.exists():
                manifest = self._existing_manifest(manifest_path, snapshot)
                return ChatGPTSharedArchiveResult(
                    import_id=import_id,
                    snapshot_path=snapshot_path,
                    manifest_path=manifest_path,
                    duplicate=True,
                    manifest=manifest,
                )
            manifest = self._manifest(import_id, snapshot)
            self.imports_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            stage = Path(
                tempfile.mkdtemp(prefix=f".{import_id}-", dir=self.imports_dir)
            )
            try:
                staged_snapshot = stage / "snapshot.html"
                staged_manifest = stage / "manifest.json"
                with staged_snapshot.open("xb") as target:
                    target.write(snapshot.content)
                    target.flush()
                    os.fsync(target.fileno())
                staged_manifest.write_text(
                    json.dumps(
                        manifest.model_dump(mode="json"), ensure_ascii=False, indent=2
                    )
                    + "\n",
                    encoding="utf-8",
                )
                staged_snapshot.chmod(0o600)
                staged_manifest.chmod(0o600)
                os.replace(stage, destination)
            except OSError as error:
                self._remove_stage(stage)
                raise ChatGPTSharedArchiveError(
                    "CHATGPT_SHARED_ARCHIVE_WRITE_FAILED",
                    "Shared snapshot could not be archived",
                ) from error
        return ChatGPTSharedArchiveResult(
            import_id=import_id,
            snapshot_path=snapshot_path,
            manifest_path=manifest_path,
            duplicate=False,
            manifest=manifest,
        )

    def _existing_manifest(
        self, manifest_path: Path, snapshot: ChatGPTSharedSnapshot
    ) -> ChatGPTSharedSnapshotManifest:
        manifest = self.load_manifest(manifest_path)
        snapshot_path = manifest_path.parent / "snapshot.html"
        try:
            stored = snapshot_path.read_bytes()
        except OSError as error:
            raise ChatGPTSharedArchiveError(
                "CHATGPT_SHARED_ARCHIVE_STORED_COPY_INVALID",
                "Stored shared snapshot cannot be read",
            ) from error
        if (
            hashlib.sha256(stored).hexdigest() != manifest.snapshot_sha256
            or manifest.snapshot_sha256 != snapshot.snapshot_sha256
            or manifest.snapshot_size != len(stored)
            or manifest.share_id_hash != self._share_id_hash(snapshot.share_id)
        ):
            raise ChatGPTSharedArchiveError(
                "CHATGPT_SHARED_ARCHIVE_STORED_COPY_INVALID",
                "Stored shared snapshot does not match its manifest",
            )
        return manifest

    @staticmethod
    def load_manifest(path: Path) -> ChatGPTSharedSnapshotManifest:
        try:
            return ChatGPTSharedSnapshotManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, ValidationError) as error:
            raise ChatGPTSharedArchiveError(
                "CHATGPT_SHARED_ARCHIVE_MANIFEST_INVALID",
                "Shared snapshot manifest is missing or invalid",
            ) from error

    def _manifest(
        self, import_id: str, snapshot: ChatGPTSharedSnapshot
    ) -> ChatGPTSharedSnapshotManifest:
        acquired_at = self.clock()
        if acquired_at.tzinfo is None or acquired_at.utcoffset() is None:
            raise ChatGPTSharedArchiveError(
                "CHATGPT_SHARED_ARCHIVE_CLOCK_INVALID",
                "Shared snapshot archive clock must include a timezone",
            )
        return ChatGPTSharedSnapshotManifest(
            import_id=import_id,
            snapshot_sha256=snapshot.snapshot_sha256,
            snapshot_size=len(snapshot.content),
            share_id_hash=self._share_id_hash(snapshot.share_id),
            content_type=snapshot.content_type,
            acquired_at=acquired_at,
        )

    @staticmethod
    def _share_id_hash(share_id: str) -> str:
        return hashlib.sha256(share_id.encode("utf-8")).hexdigest()

    def _remove_stage(self, stage: Path) -> None:
        try:
            resolved = stage.resolve()
            resolved.relative_to(self.imports_dir.resolve())
        except (OSError, ValueError):
            return
        shutil.rmtree(resolved, ignore_errors=True)
