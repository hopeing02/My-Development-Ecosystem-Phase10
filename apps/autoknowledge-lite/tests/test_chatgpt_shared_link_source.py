from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from autoknowledge_lite.chatgpt_shared_link_source import (
    ChatGPTSharedLinkSource,
    ChatGPTSharedLinkSourceError,
    canonical_chatgpt_shared_url,
)
from autoknowledge_lite.chatgpt_knowledge_adapter import ChatGPTKnowledgeAdapter
from autoknowledge_lite.knowledge_model import DataSource

SHARE_ID = "12345678-abcd-4321-abcd-1234567890ab"
SHARE_URL = f"https://chatgpt.com/share/{SHARE_ID}"


def conversation(session_id: str = SHARE_ID) -> dict[str, object]:
    return {
        "id": session_id,
        "title": "Shared design",
        "create_time": 1_700_000_000,
        "update_time": 1_700_000_100,
        "current_node": "message-1",
        "mapping": {
            "message-1": {
                "id": "message-1",
                "parent": None,
                "message": {
                    "id": "message-1",
                    "author": {"role": "user"},
                    "create_time": 1_700_000_000,
                    "content": {"parts": ["Design this"]},
                },
            }
        },
    }


def write_snapshot(path: Path, record: dict[str, object]) -> bytes:
    embedded = json.dumps({"conversation": record})
    original = f"<html><script>self.__next_f.push([1,{json.dumps(embedded)}])</script></html>".encode()
    path.write_bytes(original)
    return original


def streamed_reference_table(value: object) -> list[object]:
    table: list[object] = []

    def store(item: object) -> int:
        if item is None:
            return -5
        index = len(table)
        table.append(None)
        if isinstance(item, dict):
            encoded: dict[str, int] = {}
            table[index] = encoded
            for key, child in item.items():
                encoded[f"_{store(key)}"] = store(child)
        elif isinstance(item, list):
            encoded_list = [store(child) for child in item]
            table[index] = encoded_list
        else:
            table[index] = item
        return index

    assert store(value) == 0
    return table


def test_discovers_structured_shared_conversation_without_mutating_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "share.html"
    record = conversation()
    expected = copy.deepcopy(record)
    original = write_snapshot(snapshot, record)
    source = ChatGPTSharedLinkSource(SHARE_URL, snapshot)

    discovery = source.discover_sessions()
    projected = source.read_session(discovery.sessions[0])

    assert discovery.sessions[0].source_session_id == SHARE_ID
    assert discovery.sessions[0].source_format == "chatgpt_shared_link"
    assert projected == expected
    assert snapshot.read_bytes() == original


def test_discovers_current_streamed_loader_conversation_without_mutating_snapshot(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "share.html"
    record = conversation()
    loader = {
        "loaderData": {
            "routes/share.$shareId.($action)": {"serverResponse": {"data": record}}
        }
    }
    reference_table = streamed_reference_table(loader)
    cycle_key = len(reference_table)
    reference_table.append("cycle")
    assert isinstance(reference_table[0], dict)
    reference_table[0][f"_{cycle_key}"] = 0
    streamed = json.dumps(reference_table, separators=(",", ":"))
    original = (
        "<html><script>window.streamController.enqueue("
        f"{json.dumps(streamed)})</script></html>"
    ).encode()
    snapshot.write_bytes(original)

    source = ChatGPTSharedLinkSource(SHARE_URL, snapshot)
    discovery = source.discover_sessions()
    projected = source.read_session(discovery.sessions[0])

    assert discovery.sessions[0].source_session_id == SHARE_ID
    assert projected == record
    assert snapshot.read_bytes() == original


@pytest.mark.parametrize(
    "url",
    [
        f"http://chatgpt.com/share/{SHARE_ID}",
        f"https://example.com/share/{SHARE_ID}",
        f"https://chatgpt.com.evil.test/share/{SHARE_ID}",
        f"https://user@chatgpt.com/share/{SHARE_ID}",
        f"https://chatgpt.com:invalid/share/{SHARE_ID}",
        "https://chatgpt.com/",
    ],
)
def test_rejects_noncanonical_shared_urls(tmp_path: Path, url: str) -> None:
    snapshot = tmp_path / "share.html"
    snapshot.write_text("{}", encoding="utf-8")

    with pytest.raises(ChatGPTSharedLinkSourceError) as raised:
        ChatGPTSharedLinkSource(url, snapshot)

    assert raised.value.code == "CHATGPT_SHARED_URL_INVALID"


def test_canonicalizes_safe_mobile_copy_variants() -> None:
    assert (
        canonical_chatgpt_shared_url(f"\u200b{SHARE_URL}?source=mobile#copied\ufeff")
        == SHARE_URL
    )


def test_deduplicates_repeated_payload_and_prefers_matching_share_id(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "share.html"
    matching = conversation()
    other = conversation("other-conversation")
    snapshot.write_text(
        json.dumps({"items": [other, matching, matching]}), encoding="utf-8"
    )
    source = ChatGPTSharedLinkSource(SHARE_URL, snapshot)

    discovery = source.discover_sessions()

    assert discovery.sessions[0].source_session_id == SHARE_ID
    assert [warning.code for warning in discovery.warnings] == [
        "CHATGPT_SHARED_MULTIPLE_CONVERSATIONS"
    ]


def test_isolates_damaged_snapshot_without_changing_it(tmp_path: Path) -> None:
    snapshot = tmp_path / "share.html"
    original = b"<html><script>damaged payload</script></html>"
    snapshot.write_bytes(original)

    with pytest.raises(ChatGPTSharedLinkSourceError) as raised:
        ChatGPTSharedLinkSource(SHARE_URL, snapshot).discover_sessions()

    assert raised.value.code == "CHATGPT_SHARED_CONVERSATION_MISSING"
    assert snapshot.read_bytes() == original


def test_rejects_oversized_snapshot_before_parsing(tmp_path: Path) -> None:
    snapshot = tmp_path / "share.html"
    snapshot.write_bytes(b"x" * 11)

    with pytest.raises(ChatGPTSharedLinkSourceError) as raised:
        ChatGPTSharedLinkSource(
            SHARE_URL, snapshot, max_snapshot_bytes=10
        ).discover_sessions()

    assert raised.value.code == "CHATGPT_SHARED_SNAPSHOT_TOO_LARGE"


def test_projects_shared_payload_as_original_session_and_message(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "share.html"
    write_snapshot(snapshot, conversation())
    source = ChatGPTSharedLinkSource(SHARE_URL, snapshot)
    reference = source.discover_sessions().sessions[0]

    projection = ChatGPTKnowledgeAdapter().project(source.read_session(reference))

    assert projection.session.source_session_id == SHARE_ID
    assert projection.session.provenance.source == DataSource.ORIGINAL
    assert len(projection.messages) == 1
    assert projection.messages[0].provenance.source == DataSource.ORIGINAL
