from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from autoknowledge_lite.knowledge_model import (
    ActivityType,
    DataSource,
    Message,
    MessageRole,
    Provenance,
    Session,
    SessionSource,
    TaskStatus,
)
from autoknowledge_lite.task_analyzer import SessionTaskAnalyzer


def _session() -> Session:
    started = datetime(2026, 8, 19, 1, 0, tzinfo=UTC)
    return Session(
        session_id="session-1",
        source=SessionSource.CHATGPT,
        title="Task analyzer",
        created_at=started,
        updated_at=started + timedelta(minutes=10),
        provenance=Provenance(source=DataSource.ORIGINAL),
    )


def _message(sequence: int, role: MessageRole, content: str) -> Message:
    return Message(
        message_id=f"message-{sequence}",
        session_id="session-1",
        role=role,
        content=content,
        timestamp=datetime(2026, 8, 19, 1, sequence, tzinfo=UTC),
        sequence=sequence,
        provenance=Provenance(source=DataSource.ORIGINAL),
    )


def test_splits_only_high_confidence_task_boundary() -> None:
    messages = [
        _message(1, MessageRole.USER, "Adapter를 구현해줘"),
        _message(2, MessageRole.ASSISTANT, "구현을 완료했습니다."),
        _message(3, MessageRole.USER, "다음 작업: Viewer 테스트를 추가해줘"),
        _message(4, MessageRole.ASSISTANT, "테스트를 완료했습니다."),
    ]

    result = SessionTaskAnalyzer().analyze(_session(), messages)

    assert [task.message_range.model_dump() for task in result.tasks] == [
        {"start_sequence": 1, "end_sequence": 2},
        {"start_sequence": 3, "end_sequence": 4},
    ]
    assert [task.status for task in result.tasks] == [
        TaskStatus.COMPLETED,
        TaskStatus.COMPLETED,
    ]
    assert result.tasks[1].provenance.confidence == 0.95
    assert result.boundary_candidates == ()


def test_keeps_uncertain_boundary_as_candidate_without_splitting() -> None:
    messages = [
        _message(1, MessageRole.USER, "설계를 검토해줘"),
        _message(2, MessageRole.ASSISTANT, "검토 중입니다."),
        _message(3, MessageRole.USER, "다음 단계도 확인해줘"),
        _message(4, MessageRole.ASSISTANT, "확인 중입니다."),
    ]

    result = SessionTaskAnalyzer().analyze(_session(), messages)

    assert len(result.tasks) == 1
    assert result.tasks[0].message_range.end_sequence == 4
    assert len(result.boundary_candidates) == 1
    assert result.boundary_candidates[0].message_sequence == 3
    assert result.boundary_candidates[0].confidence == 0.45
    assert result.boundary_candidates[0].provenance.source == DataSource.DERIVED


def test_creates_request_response_decision_note_and_result_activities() -> None:
    messages = [
        _message(1, MessageRole.USER, "저장 방식을 정해줘"),
        _message(2, MessageRole.ASSISTANT, "JSON 방식을 선택했습니다."),
        _message(3, MessageRole.TOOL, "pytest output"),
        _message(4, MessageRole.ASSISTANT, "작업을 완료했습니다."),
    ]

    result = SessionTaskAnalyzer().analyze(_session(), messages)

    assert [activity.activity_type for activity in result.activities] == [
        ActivityType.REQUEST,
        ActivityType.DECISION,
        ActivityType.NOTE,
        ActivityType.RESULT,
    ]
    assert all(
        activity.provenance.source == DataSource.DERIVED
        for activity in result.activities
    )


def test_isolates_invalid_messages_and_does_not_mutate_originals() -> None:
    session = _session()
    valid = _message(1, MessageRole.USER, "원본을 보존해줘")
    duplicate = _message(1, MessageRole.ASSISTANT, "중복 sequence")
    mismatch = duplicate.model_copy(
        update={"message_id": "foreign", "session_id": "other", "sequence": 2}
    )
    originals = deepcopy([valid, duplicate, mismatch])

    result = SessionTaskAnalyzer().analyze(session, [valid, duplicate, mismatch])

    assert len(result.tasks) == 1
    assert set(result.warnings) == {
        "TASK_MESSAGE_SEQUENCE_DUPLICATE",
        "TASK_MESSAGE_SESSION_MISMATCH",
    }
    assert [valid, duplicate, mismatch] == originals


def test_does_not_create_task_without_real_user_request() -> None:
    messages = [_message(1, MessageRole.ASSISTANT, "자동 생성하지 않음")]

    result = SessionTaskAnalyzer().analyze(_session(), messages)

    assert result.tasks == ()
    assert result.activities == ()
    assert result.warnings == ("TASK_USER_REQUEST_MISSING",)


def test_uses_latest_result_when_a_failed_attempt_is_recovered() -> None:
    messages = [
        _message(1, MessageRole.USER, "오류를 수정해줘"),
        _message(2, MessageRole.ASSISTANT, "첫 실행은 실패했습니다."),
        _message(3, MessageRole.USER, "원인을 수정하고 다시 실행해줘"),
        _message(4, MessageRole.ASSISTANT, "수정과 검증을 완료했습니다."),
    ]

    result = SessionTaskAnalyzer().analyze(_session(), messages)

    assert len(result.tasks) == 1
    assert result.tasks[0].status == TaskStatus.COMPLETED
