from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from autoknowledge_lite.knowledge_model import (
    Activity,
    ActivityType,
    DataSource,
    DerivationMethod,
    FileChangeType,
    FileRecord,
    Message,
    MessageRange,
    MessageRole,
    Provenance,
    Session,
    SessionSource,
    Task,
    TaskBoundaryStatus,
    TaskStatus,
)

ORIGINAL = Provenance(source=DataSource.ORIGINAL, source_refs=("capture:cap_1",))
DERIVED = Provenance(
    source=DataSource.DERIVED,
    derived_by=DerivationMethod.RULE,
    confidence=0.8,
    source_refs=("message:msg_1",),
)


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_session_and_message_preserve_original_content() -> None:
    session = Session(
        session_id="session_1",
        source=SessionSource.CODEX,
        title="공통 모델 구현",
        created_at=timestamp("2026-08-18T10:00:00+09:00"),
        updated_at=timestamp("2026-08-18T10:05:00+09:00"),
        capture_id="cap_1",
        message_ids=("msg_1",),
        provenance=ORIGINAL,
    )
    content = "  원본의 앞뒤 공백도 변경하지 않는다.  "
    message = Message(
        message_id="msg_1",
        session_id=session.session_id,
        role=MessageRole.USER,
        content=content,
        timestamp=timestamp("2026-08-18T10:01:00+09:00"),
        sequence=1,
        provenance=ORIGINAL,
    )

    assert message.content == content
    assert session.model_dump(mode="json")["source"] == "codex"
    assert message.model_dump(mode="json")["role"] == "user"


def test_task_and_activity_keep_derived_boundary_separate() -> None:
    task = Task(
        task_id="task_1",
        session_id="session_1",
        title="공통 모델 추가",
        status=TaskStatus.IN_PROGRESS,
        boundary_status=TaskBoundaryStatus.SUGGESTED,
        message_range=MessageRange(start_sequence=1, end_sequence=3),
        activity_ids=("activity_1",),
        provenance=DERIVED,
    )
    activity = Activity(
        activity_id="activity_1",
        task_id=task.task_id,
        activity_type=ActivityType.REQUEST,
        sequence=1,
        entity_refs=("message:msg_1",),
        provenance=DERIVED,
    )

    assert task.provenance.source == DataSource.DERIVED
    assert task.provenance.confidence == 0.8
    assert activity.entity_refs == ("message:msg_1",)


def test_invalid_ranges_and_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValidationError, match="end_sequence"):
        MessageRange(start_sequence=3, end_sequence=2)

    with pytest.raises(ValidationError, match="timezone"):
        Session(
            session_id="session_1",
            source=SessionSource.OTHER,
            title="잘못된 시각",
            created_at=datetime(2026, 8, 18, 10, 0),
            updated_at=datetime(2026, 8, 18, 10, 1),
            provenance=ORIGINAL,
        )


def test_provenance_requires_explicit_derivation_method() -> None:
    with pytest.raises(ValidationError, match="derived_by"):
        Provenance(source=DataSource.DERIVED, confidence=0.5)

    with pytest.raises(ValidationError, match="cannot declare"):
        Provenance(
            source=DataSource.ORIGINAL,
            derived_by=DerivationMethod.AI,
            confidence=0.5,
        )


def test_renamed_file_requires_previous_path() -> None:
    with pytest.raises(ValidationError, match="previous_path"):
        FileRecord(
            file_id="file_1",
            task_id="task_1",
            path="new.py",
            change_type=FileChangeType.RENAMED,
            provenance=ORIGINAL,
        )
