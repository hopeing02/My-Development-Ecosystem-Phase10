from __future__ import annotations

from copy import deepcopy

import pytest

from autoknowledge_lite.capture_api import CaptureEnvelope
from autoknowledge_lite.codex_knowledge_adapter import (
    CodexKnowledgeAdapter,
    CodexKnowledgeAdapterError,
)
from autoknowledge_lite.knowledge_model import (
    ActivityType,
    DataSource,
    FileChangeType,
    MessageRole,
    TestStatus as KnowledgeTestStatus,
)


def envelope() -> CaptureEnvelope:
    return CaptureEnvelope.model_validate(
        {
            "schemaVersion": "1.0",
            "captureId": "cap_codex_1",
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "captureMethod": "windows_codex_session",
            "projectId": "autoknowledge-lite",
            "targetFolder": "40_Reference",
            "parentDocument": None,
            "capturedAt": "2026-08-18T10:30:00+09:00",
            "deviceId": "windows-test",
            "contentHash": "a" * 64,
            "metadata": {},
            "payload": {
                "captureSessionId": "capture_session_1",
                "sourceSessionId": "source_session_1",
                "clientType": "codex_app_server",
                "title": "Codex 공통 모델 연결",
                "startedAt": "2026-08-18T10:00:00+09:00",
                "endedAt": "2026-08-18T10:25:00+09:00",
                "adapter": {
                    "adapterName": "CodexAppSessionAdapter",
                    "adapterVersion": "1.0.0",
                },
                "messages": [
                    {
                        "messageId": "msg_user",
                        "sourceMessageId": "source_user",
                        "sequence": 1,
                        "role": "user",
                        "content": "  원문 공백을 보존해줘.  ",
                        "contentHash": "b" * 64,
                        "createdAt": "2026-08-18T10:01:00+09:00",
                    },
                    {
                        "messageId": "msg_summary",
                        "sequence": 2,
                        "role": "system_summary",
                        "content": "공개 compaction 요약",
                        "createdAt": "2026-08-18T10:02:00+09:00",
                    },
                ],
                "commands": [
                    {
                        "commandId": "cmd_test",
                        "command": "uv run pytest",
                        "startedAt": "2026-08-18T10:20:00+09:00",
                        "endedAt": "2026-08-18T10:21:00+09:00",
                        "exitCode": 0,
                        "stdout": "48 passed",
                        "stderr": "",
                    }
                ],
                "changedFiles": [
                    {
                        "path": "apps/autoknowledge-lite/src/app.py",
                        "changeType": "modified",
                        "addedLines": 12,
                        "deletedLines": 3,
                    }
                ],
                "tests": [
                    {
                        "testId": "test_pytest",
                        "commandId": "cmd_test",
                        "framework": "pytest",
                        "status": "PASSED",
                        "exitCode": 0,
                    }
                ],
            },
        }
    )


def test_projects_codex_session_and_messages_without_mutating_source() -> None:
    source = envelope()
    original_payload = deepcopy(source.payload)

    projection = CodexKnowledgeAdapter().project(source)

    assert source.payload == original_payload
    assert projection.session.session_id == "capture_session_1"
    assert projection.session.source_session_id == "source_session_1"
    assert projection.session.message_ids == ("msg_user", "msg_summary")
    assert projection.session.task_ids == ("task:cap_codex_1:session",)
    assert projection.session.provenance.source == DataSource.ORIGINAL
    assert projection.messages[0].content == "  원문 공백을 보존해줘.  "
    assert projection.messages[0].role == MessageRole.USER
    assert projection.messages[1].role == MessageRole.SYSTEM
    assert projection.commands[0].command_id == "cmd_test"
    assert projection.commands[0].command == "uv run pytest"
    assert projection.commands[0].stdout == "48 passed"
    assert projection.commands[0].provenance.source == DataSource.ORIGINAL
    assert projection.files[0].path == "apps/autoknowledge-lite/src/app.py"
    assert projection.files[0].change_type == FileChangeType.MODIFIED
    assert projection.files[0].added_lines == 12
    assert projection.tests[0].test_id == "test_pytest"
    assert projection.tests[0].command_id == "cmd_test"
    assert projection.tests[0].status == KnowledgeTestStatus.PASSED
    assert [activity.activity_type for activity in projection.activities] == [
        ActivityType.COMMAND,
        ActivityType.FILE_CHANGE,
        ActivityType.TEST,
    ]
    assert [activity.sequence for activity in projection.activities] == [1, 2, 3]
    assert all(
        activity.provenance.source == DataSource.DERIVED
        for activity in projection.activities
    )
    assert projection.warnings == ()


def test_falls_back_to_existing_capture_id_and_capture_time() -> None:
    source = envelope()
    source.payload["captureSessionId"] = None
    source.payload["endedAt"] = None

    projection = CodexKnowledgeAdapter().project(source)

    assert projection.session.session_id == source.capture_id
    assert projection.session.updated_at == source.captured_at


def test_skips_unmappable_messages_and_reports_warnings() -> None:
    source = envelope()
    source.payload["messages"] = [
        {"sequence": 1, "role": "user", "content": "ID 없음"},
        {
            "messageId": "bad_sequence",
            "sequence": 0,
            "role": "user",
            "content": "순서 오류",
        },
        {
            "messageId": "bad_role",
            "sequence": 2,
            "role": "unknown",
            "content": "지원하지 않는 역할",
        },
        {
            "messageId": "valid",
            "sequence": 3,
            "role": "assistant",
            "content": "보존되는 메시지",
            "contentHash": "INVALID",
            "createdAt": "not-a-time",
        },
        {
            "messageId": "valid",
            "sequence": 4,
            "role": "assistant",
            "content": "중복 ID",
        },
    ]

    projection = CodexKnowledgeAdapter().project(source)

    assert [message.message_id for message in projection.messages] == ["valid"]
    assert projection.messages[0].content_hash is None
    assert projection.messages[0].timestamp is None
    assert set(projection.warnings) == {
        "CODEX_MESSAGE_HASH_INVALID",
        "CODEX_MESSAGE_ID_DUPLICATE",
        "CODEX_MESSAGE_ID_MISSING",
        "CODEX_MESSAGE_ROLE_UNSUPPORTED",
        "CODEX_MESSAGE_SEQUENCE_INVALID",
        "CODEX_MESSAGE_TIMESTAMP_INVALID",
    }


def test_skips_invalid_activity_records_and_preserves_valid_records() -> None:
    source = envelope()
    original_payload = deepcopy(source.payload)
    source.payload["commands"] = [
        {"commandId": "missing_text"},
        {"commandId": "duplicate", "command": "uv run ruff check ."},
        {"commandId": "duplicate", "command": "uv run black --check ."},
    ]
    source.payload["changedFiles"] = [
        {"path": "bad.txt", "changeType": "unknown"},
        {"path": "renamed.txt", "changeType": "renamed"},
        {"path": "valid.txt", "changeType": "added"},
    ]
    source.payload["tests"] = [
        {"testId": "missing_command", "status": "PASSED"},
        {
            "testId": "valid_test",
            "commandId": "duplicate",
            "status": "FAILED",
            "exitCode": 1,
        },
    ]
    expected_payload = deepcopy(source.payload)

    projection = CodexKnowledgeAdapter().project(source)

    assert source.payload == expected_payload
    assert original_payload != source.payload
    assert [command.command_id for command in projection.commands] == ["duplicate"]
    assert [file.path for file in projection.files] == ["valid.txt"]
    assert [test.test_id for test in projection.tests] == ["valid_test"]
    assert projection.tests[0].command == "uv run ruff check ."
    assert set(projection.warnings) >= {
        "CODEX_COMMAND_ID_DUPLICATE",
        "CODEX_COMMAND_TEXT_MISSING",
        "CODEX_FILE_CHANGE_TYPE_UNSUPPORTED",
        "CODEX_FILE_RENAME_SOURCE_MISSING",
        "CODEX_TEST_COMMAND_MISSING",
    }


def test_projects_renamed_file_and_synthesizes_missing_record_ids() -> None:
    source = envelope()
    source.payload["commands"][0].pop("commandId")
    source.payload["changedFiles"] = [
        {
            "path": "new-name.py",
            "oldPath": "old-name.py",
            "changeType": "renamed",
        }
    ]
    source.payload["tests"] = [
        {
            "command": "uv run pytest",
            "status": "SKIPPED",
        }
    ]

    projection = CodexKnowledgeAdapter().project(source)

    assert projection.commands[0].command_id.endswith(":001")
    assert projection.files[0].previous_path == "old-name.py"
    assert projection.tests[0].test_id == "test:cap_codex_1:001"
    assert projection.tests[0].status == KnowledgeTestStatus.SKIPPED


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("source_type", "chatgpt", "INVALID_CODEX_SOURCE"),
        ("capture_type", "clipboard_item", "INVALID_CODEX_CAPTURE_TYPE"),
    ],
)
def test_rejects_non_codex_session_captures(field: str, value: str, code: str) -> None:
    source = envelope().model_copy(update={field: value})

    with pytest.raises(CodexKnowledgeAdapterError) as captured:
        CodexKnowledgeAdapter().project(source)

    assert captured.value.code == code
