"""Deterministic, read-only Task analysis for AI conversation sessions."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from autoknowledge_lite.knowledge_model import (
    Activity,
    ActivityType,
    DataSource,
    DerivationMethod,
    KnowledgeModel,
    Message,
    MessageRange,
    MessageRole,
    Provenance,
    Session,
    Task,
    TaskBoundaryStatus,
    TaskStatus,
)


class TaskBoundaryCandidate(KnowledgeModel):
    """An uncertain boundary that must not split a Task automatically."""

    message_sequence: int = Field(ge=1)
    confidence: float = Field(ge=0, le=1)
    reasons: tuple[str, ...]
    provenance: Provenance


class TaskAnalysis(KnowledgeModel):
    tasks: tuple[Task, ...] = ()
    activities: tuple[Activity, ...] = ()
    boundary_candidates: tuple[TaskBoundaryCandidate, ...] = ()
    warnings: tuple[str, ...] = ()


class SessionTaskAnalyzer:
    """Suggest Tasks without mutating or replacing original Session messages."""

    _EXPLICIT_BOUNDARY_MARKERS = (
        "new task",
        "next task",
        "separate task",
        "새 작업",
        "새로운 작업",
        "다음 작업",
        "별도 작업",
    )
    _PHASE_BOUNDARY_MARKERS = (
        "next step",
        "다음 단계",
        "이제 구현",
        "이제 테스트",
    )
    _COMPLETION_MARKERS = (
        "completed",
        "done",
        "finished",
        "완료했습니다",
        "완료됐",
        "마무리했습니다",
    )
    _FAILURE_MARKERS = (
        "task failed",
        "failed to",
        "실패했습니다",
        "완료하지 못했습니다",
    )
    _DECISION_MARKERS = (
        "decided",
        "we will use",
        "선택했습니다",
        "결정했습니다",
        "채택했습니다",
    )

    def analyze(self, session: Session, messages: Sequence[Message]) -> TaskAnalysis:
        warnings: list[str] = []
        ordered = self._valid_messages(session, messages, warnings)
        user_indexes = [
            index
            for index, message in enumerate(ordered)
            if message.role == MessageRole.USER and message.content.strip()
        ]
        if not user_indexes:
            return TaskAnalysis(
                warnings=tuple(sorted(set(warnings + ["TASK_USER_REQUEST_MISSING"])))
            )

        starts = [user_indexes[0]]
        start_confidence = {user_indexes[0]: 1.0}
        candidates: list[TaskBoundaryCandidate] = []
        for index in user_indexes[1:]:
            score, reasons = self._boundary_score(ordered, starts[-1], index)
            if score >= 0.75:
                starts.append(index)
                start_confidence[index] = score
            elif score >= 0.4:
                message = ordered[index]
                candidates.append(
                    TaskBoundaryCandidate(
                        message_sequence=message.sequence,
                        confidence=score,
                        reasons=reasons,
                        provenance=self._provenance(
                            score,
                            f"session:{session.session_id}",
                            f"message:{message.message_id}",
                        ),
                    )
                )

        tasks: list[Task] = []
        activities: list[Activity] = []
        for task_index, start in enumerate(starts, 1):
            end = starts[task_index] if task_index < len(starts) else len(ordered)
            segment = ordered[start:end]
            task, task_activities = self._task(
                session,
                segment,
                start_confidence[start],
            )
            tasks.append(task)
            activities.extend(task_activities)
        return TaskAnalysis(
            tasks=tuple(tasks),
            activities=tuple(activities),
            boundary_candidates=tuple(candidates),
            warnings=tuple(sorted(set(warnings))),
        )

    @staticmethod
    def _valid_messages(
        session: Session, messages: Sequence[Message], warnings: list[str]
    ) -> list[Message]:
        ordered: list[Message] = []
        seen_sequences: set[int] = set()
        for message in sorted(messages, key=lambda item: item.sequence):
            if message.session_id != session.session_id:
                warnings.append("TASK_MESSAGE_SESSION_MISMATCH")
                continue
            if message.sequence in seen_sequences:
                warnings.append("TASK_MESSAGE_SEQUENCE_DUPLICATE")
                continue
            seen_sequences.add(message.sequence)
            ordered.append(message)
        return ordered

    def _boundary_score(
        self, messages: Sequence[Message], start: int, current: int
    ) -> tuple[float, tuple[str, ...]]:
        content = messages[current].content.casefold()
        score = 0.0
        reasons: list[str] = []
        if self._contains(content, self._EXPLICIT_BOUNDARY_MARKERS):
            score += 0.7
            reasons.append("explicit_new_task")
        if self._contains(content, self._PHASE_BOUNDARY_MARKERS):
            score += 0.45
            reasons.append("phase_transition")
        previous_assistant = "\n".join(
            message.content.casefold()
            for message in messages[start:current]
            if message.role == MessageRole.ASSISTANT
        )
        if self._contains(previous_assistant, self._COMPLETION_MARKERS):
            score += 0.25
            reasons.append("previous_completion")
        return min(score, 1.0), tuple(reasons)

    def _task(
        self,
        session: Session,
        messages: Sequence[Message],
        confidence: float,
    ) -> tuple[Task, tuple[Activity, ...]]:
        first = messages[0]
        task_id = f"task:{session.session_id}:{first.sequence:04d}"
        activities = tuple(
            self._activity(task_id, message, index)
            for index, message in enumerate(messages, 1)
        )
        status = self._task_status(messages)
        terminal = status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
        title = first.content.strip().splitlines()[0][:120]
        task = Task(
            task_id=task_id,
            session_id=session.session_id,
            title=title,
            status=status,
            boundary_status=TaskBoundaryStatus.SUGGESTED,
            started_at=first.timestamp,
            completed_at=messages[-1].timestamp if terminal else None,
            message_range=MessageRange(
                start_sequence=first.sequence,
                end_sequence=messages[-1].sequence,
            ),
            activity_ids=tuple(item.activity_id for item in activities),
            provenance=self._provenance(
                confidence,
                f"session:{session.session_id}",
                *(f"message:{message.message_id}" for message in messages),
            ),
        )
        return task, activities

    def _activity(self, task_id: str, message: Message, sequence: int) -> Activity:
        activity_type = self._activity_type(message)
        return Activity(
            activity_id=(
                f"activity:{task_id}:{message.sequence:04d}:{activity_type.value}"
            ),
            task_id=task_id,
            activity_type=activity_type,
            sequence=sequence,
            timestamp=message.timestamp,
            summary=message.content.strip()[:240] or None,
            entity_refs=(message.message_id,),
            provenance=self._provenance(1.0, f"message:{message.message_id}"),
        )

    def _activity_type(self, message: Message) -> ActivityType:
        content = message.content.casefold()
        if message.role == MessageRole.USER:
            return ActivityType.REQUEST
        if message.role == MessageRole.ASSISTANT:
            if self._contains(
                content, self._FAILURE_MARKERS + self._COMPLETION_MARKERS
            ):
                return ActivityType.RESULT
            if self._contains(content, self._DECISION_MARKERS):
                return ActivityType.DECISION
            return ActivityType.RESPONSE
        return ActivityType.NOTE

    def _task_status(self, messages: Sequence[Message]) -> TaskStatus:
        assistant_messages = [
            message.content.casefold()
            for message in messages
            if message.role == MessageRole.ASSISTANT
        ]
        if not assistant_messages:
            return TaskStatus.IN_PROGRESS
        latest = assistant_messages[-1]
        if self._contains(latest, self._FAILURE_MARKERS):
            return TaskStatus.FAILED
        if self._contains(latest, self._COMPLETION_MARKERS):
            return TaskStatus.COMPLETED
        return TaskStatus.IN_PROGRESS

    @staticmethod
    def _contains(content: str, markers: Sequence[str]) -> bool:
        return any(marker in content for marker in markers)

    @staticmethod
    def _provenance(confidence: float, *source_refs: str) -> Provenance:
        return Provenance(
            source=DataSource.DERIVED,
            derived_by=DerivationMethod.RULE,
            confidence=confidence,
            source_refs=source_refs,
        )
