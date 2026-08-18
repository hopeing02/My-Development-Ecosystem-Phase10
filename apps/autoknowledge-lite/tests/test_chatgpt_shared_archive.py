from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from autoknowledge_lite.chatgpt_shared_archive import (
    ChatGPTSharedArchiveError,
    ChatGPTSharedFetchError,
    ChatGPTSharedSnapshot,
    ChatGPTSharedSnapshotFetcher,
    ChatGPTSharedSnapshotStore,
)

SHARE_ID = "12345678-abcd-4321-abcd-1234567890ab"
SHARE_URL = f"https://chatgpt.com/share/{SHARE_ID}"


def client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def snapshot(content: bytes = b"<html>conversation</html>") -> ChatGPTSharedSnapshot:
    return ChatGPTSharedSnapshot(
        shared_url=SHARE_URL,
        share_id=SHARE_ID,
        content=content,
        content_type="text/html",
        snapshot_sha256=hashlib.sha256(content).hexdigest(),
    )


def test_fetches_only_explicit_html_snapshot_without_credentials() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html; charset=utf-8"},
            content=b"<html>shared</html>",
        )

    fetched = ChatGPTSharedSnapshotFetcher(client(handler)).fetch(SHARE_URL)

    assert fetched.content == b"<html>shared</html>"
    assert fetched.share_id == SHARE_ID
    assert "authorization" not in requests[0].headers
    assert "cookie" not in requests[0].headers


def test_rejects_redirect_to_another_conversation() -> None:
    other_url = "https://chatgpt.com/share/other-conversation"

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": other_url})

    with pytest.raises(ChatGPTSharedFetchError) as raised:
        ChatGPTSharedSnapshotFetcher(client(handler)).fetch(SHARE_URL)

    assert raised.value.code == "CHATGPT_SHARED_REDIRECT_REJECTED"


@pytest.mark.parametrize(
    ("headers", "content"),
    [
        ({"Content-Type": "application/octet-stream"}, b"small"),
        ({"Content-Type": "text/html", "Content-Length": "11"}, b"small"),
        ({"Content-Type": "text/html"}, b"x" * 11),
    ],
)
def test_rejects_unsupported_or_oversized_responses(
    headers: dict[str, str], content: bytes
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers=headers, content=content)

    with pytest.raises(ChatGPTSharedFetchError):
        ChatGPTSharedSnapshotFetcher(client(handler), max_snapshot_bytes=10).fetch(
            SHARE_URL
        )


def test_archives_snapshot_atomically_and_deduplicates(tmp_path: Path) -> None:
    store = ChatGPTSharedSnapshotStore(
        tmp_path, clock=lambda: datetime(2026, 8, 18, tzinfo=UTC)
    )
    source = snapshot()

    first = store.archive(source)
    second = store.archive(source)

    assert first.duplicate is False
    assert second.duplicate is True
    assert first.snapshot_path.read_bytes() == source.content
    assert first.manifest.acquisition_method == "shared_link"
    assert SHARE_ID not in first.manifest_path.read_text(encoding="utf-8")
    assert not list(store.imports_dir.glob(".*"))


def test_refuses_corrupted_existing_archive(tmp_path: Path) -> None:
    store = ChatGPTSharedSnapshotStore(tmp_path)
    source = snapshot()
    archived = store.archive(source)
    archived.snapshot_path.write_bytes(b"changed")

    with pytest.raises(ChatGPTSharedArchiveError) as raised:
        store.archive(source)

    assert raised.value.code == "CHATGPT_SHARED_ARCHIVE_STORED_COPY_INVALID"


def test_rejects_snapshot_whose_content_changed_before_archive(tmp_path: Path) -> None:
    source = snapshot()
    changed = ChatGPTSharedSnapshot(
        shared_url=source.shared_url,
        share_id=source.share_id,
        content=b"changed",
        content_type=source.content_type,
        snapshot_sha256=source.snapshot_sha256,
    )

    with pytest.raises(ChatGPTSharedArchiveError) as raised:
        ChatGPTSharedSnapshotStore(tmp_path).archive(changed)

    assert raised.value.code == "CHATGPT_SHARED_SNAPSHOT_HASH_MISMATCH"
