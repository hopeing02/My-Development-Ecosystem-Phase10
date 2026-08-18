from __future__ import annotations

from copy import deepcopy

import pytest

from autoknowledge_lite.capture_api import CaptureEnvelope
from autoknowledge_lite.chatgpt_knowledge_adapter import (
    ChatGPTKnowledgeAdapter,
    ChatGPTKnowledgeAdapterError,
)
from autoknowledge_lite.knowledge_model import (
    DataSource,
    DerivationMethod,
    MessageRole,
)


def chatgpt_export() -> dict[str, object]:
    return {
        "id": "chatgpt-session-1",
        "title": "ChatGPT Adapter 설계",
        "create_time": 1787011200.0,
        "update_time": 1787011260.0,
        "current_node": "assistant-node",
        "mapping": {
            "root": {"id": "root", "parent": None, "message": None},
            "user-node": {
                "id": "user-node",
                "parent": "root",
                "message": {
                    "id": "message-user",
                    "author": {"role": "user"},
                    "create_time": 1787011201.0,
                    "content": {"content_type": "text", "parts": [" 원문 질문 "]},
                },
            },
            "assistant-node": {
                "id": "assistant-node",
                "parent": "user-node",
                "message": {
                    "id": "message-assistant",
                    "author": {"role": "assistant"},
                    "create_time": 1787011202.0,
                    "content": {"content_type": "text", "parts": [" 원문 답변 "]},
                },
            },
        },
    }


def chatgpt_clip() -> CaptureEnvelope:
    return CaptureEnvelope.model_validate(
        {
            "schemaVersion": "1.0",
            "captureId": "cap_chatgpt_1",
            "sourceType": "chatgpt",
            "captureType": "clipboard_item",
            "captureDevice": "android",
            "captureMethod": "android_clipboard",
            "projectId": "autoknowledge-lite",
            "targetFolder": "40_Reference",
            "parentDocument": None,
            "capturedAt": "2026-08-18T10:30:00+09:00",
            "deviceId": "android-test",
            "contentHash": "a" * 64,
            "metadata": {"sourceApp": "chatgpt_android"},
            "payload": {
                "content": "  기존 ChatGPT Clip 원문  ",
                "title": None,
                "mimeType": "text/plain",
                "language": "ko",
            },
        }
    )


def test_projects_normal_chatgpt_export_to_common_session_and_messages() -> None:
    projection = ChatGPTKnowledgeAdapter().project(chatgpt_export())

    assert projection.session.session_id == "chatgpt-session-1"
    assert projection.session.source_session_id == "chatgpt-session-1"
    assert projection.session.message_ids == ("message-user", "message-assistant")
    assert projection.session.provenance.source == DataSource.ORIGINAL
    assert [message.role for message in projection.messages] == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
    ]
    assert [message.content for message in projection.messages] == [
        " 원문 질문 ",
        " 원문 답변 ",
    ]
    assert [message.sequence for message in projection.messages] == [1, 2]
    assert all(message.content_hash is None for message in projection.messages)
    assert all(
        message.provenance.source == DataSource.ORIGINAL
        for message in projection.messages
    )
    assert projection.warnings == ()


def test_projects_existing_chatgpt_clip_without_changing_its_format() -> None:
    source = chatgpt_clip()

    projection = ChatGPTKnowledgeAdapter().project(source)

    assert projection.session.session_id == "cap_chatgpt_1"
    assert projection.session.capture_id == "cap_chatgpt_1"
    assert projection.session.title == "cap_chatgpt_1"
    assert projection.session.provenance.source == DataSource.DERIVED
    assert projection.session.provenance.derived_by == DerivationMethod.RULE
    assert projection.messages[0].message_id == "cap_chatgpt_1"
    assert projection.messages[0].content == "  기존 ChatGPT Clip 원문  "
    assert projection.messages[0].content_hash == "a" * 64
    assert projection.messages[0].timestamp is None
    assert projection.messages[0].provenance.source == DataSource.DERIVED
    assert projection.warnings == ("CHATGPT_CLIP_TITLE_MISSING",)


def test_deduplicates_messages_by_source_id_and_content_hash_strategy() -> None:
    source = chatgpt_export()
    source["messages"] = [
        {
            "id": "one",
            "role": "assistant",
            "content": "동일 메시지",
        },
        {
            "id": "one",
            "role": "assistant",
            "content": "ID 중복",
        },
        {
            "id": "two",
            "role": "assistant",
            "content": " 동일 메시지 \r\n",
        },
    ]
    source.pop("mapping")
    source.pop("current_node")

    projection = ChatGPTKnowledgeAdapter().project(source)

    assert [message.message_id for message in projection.messages] == ["one"]
    assert set(projection.warnings) == {
        "CHATGPT_MESSAGE_CONTENT_DUPLICATE",
        "CHATGPT_MESSAGE_ID_DUPLICATE",
    }


def test_isolates_damaged_messages_as_warnings_and_keeps_valid_messages() -> None:
    source = chatgpt_export()
    source["messages"] = [
        {"role": "user", "content": "ID 없음"},
        {"id": "bad-role", "role": "developer", "content": "지원 불가"},
        {"id": "bad-content", "role": "assistant", "content": {"parts": []}},
        {
            "id": "valid",
            "role": "assistant",
            "content": "보존되는 원문",
            "create_time": "invalid",
            "contentHash": "INVALID",
        },
    ]
    source.pop("mapping")
    source.pop("current_node")

    projection = ChatGPTKnowledgeAdapter().project(source)

    assert [message.message_id for message in projection.messages] == ["valid"]
    assert projection.messages[0].content == "보존되는 원문"
    assert projection.messages[0].timestamp is None
    assert projection.messages[0].content_hash is None
    assert set(projection.warnings) == {
        "CHATGPT_MESSAGE_CONTENT_MISSING",
        "CHATGPT_MESSAGE_HASH_INVALID",
        "CHATGPT_MESSAGE_ID_MISSING",
        "CHATGPT_MESSAGE_ROLE_UNSUPPORTED",
        "CHATGPT_MESSAGE_TIMESTAMP_INVALID",
    }


def test_projection_does_not_mutate_chatgpt_export_or_clip_payload() -> None:
    export_source = chatgpt_export()
    clip_source = chatgpt_clip()
    original_export = deepcopy(export_source)
    original_payload = deepcopy(clip_source.payload)

    adapter = ChatGPTKnowledgeAdapter()
    adapter.project(export_source)
    adapter.project(clip_source)

    assert export_source == original_export
    assert clip_source.payload == original_payload


def test_does_not_invent_required_missing_session_data() -> None:
    source = chatgpt_export()
    source.pop("title")

    with pytest.raises(ChatGPTKnowledgeAdapterError) as captured:
        ChatGPTKnowledgeAdapter().project(source)

    assert captured.value.code == "CHATGPT_SESSION_TITLE_MISSING"
