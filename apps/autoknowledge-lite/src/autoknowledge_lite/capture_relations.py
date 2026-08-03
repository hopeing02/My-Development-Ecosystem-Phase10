"""Rule-based relations between Android excerpts and Windows Codex sessions."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from threading import Lock
from typing import Any, ClassVar
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field


class RelationStatus(StrEnum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    STALE = "stale"
    REMOVED = "removed"


class RelationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RelationEvidence(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    clipboard_content_hash: str = Field(alias="clipboardContentHash")
    matched_message_id: str | None = Field(default=None, alias="matchedMessageId")
    matched_message_ids: list[str] = Field(
        default_factory=list, alias="matchedMessageIds"
    )
    matched_content_hash: str | None = Field(default=None, alias="matchedContentHash")
    match_ratio: float = Field(default=0.0, alias="matchRatio", ge=0, le=1)
    time_delta_seconds: int | None = Field(default=None, alias="timeDeltaSeconds")
    same_project: bool | None = Field(default=None, alias="sameProject")
    target_revision: int = Field(default=1, alias="targetRevision", ge=1)


class CaptureRelation(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    relation_id: str = Field(alias="relationId")
    relation_type: str = Field(default="excerpt_of", alias="relationType")
    from_entity_type: str = Field(default="capture", alias="fromEntityType")
    from_capture_id: str = Field(alias="fromCaptureId")
    to_entity_type: str = Field(default="capture", alias="toEntityType")
    to_capture_id: str = Field(alias="toCaptureId")
    status: RelationStatus
    confidence: RelationConfidence
    score: int = Field(ge=0)
    match_method: str = Field(alias="matchMethod")
    evidence: RelationEvidence
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    created_by: str = Field(alias="createdBy")
    metadata: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class MatchingPolicy:
    window_hours: int = 24
    minimum_substring_chars: int = 100
    minimum_substring_ratio: float = 0.80
    max_substring_candidate_sessions: int = 20
    max_contiguous_messages: int = 5
    confirmed_score: int = 100
    suggested_score: int = 75
    exact_score: int = 100
    substring_95_score: int = 80
    substring_80_score: int = 60
    contiguous_score: int = 70
    same_project_score: int = 20
    same_client_score: int = 5


@dataclass(frozen=True)
class MatchCandidate:
    target_capture_id: str
    target_title: str
    score: int
    method: str
    evidence: RelationEvidence


class CaptureRelationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CaptureRelationRepository:
    """Atomically stores matching metadata, relations, and retry jobs."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.captures_path = self.root / "capture-match-index-v1.json"
        self.relations_path = self.root / "capture-relations-v1.json"
        self.jobs_path = self.root / "capture-relation-jobs-v1.json"
        self._lock = Lock()

    def upsert_capture(self, record: dict[str, Any]) -> None:
        with self._lock:
            records = self._read(self.captures_path, {})
            records[record["captureId"]] = record
            self._write(self.captures_path, records)

    def capture(self, capture_id: str) -> dict[str, Any] | None:
        return self._read(self.captures_path, {}).get(capture_id)

    def captures(self) -> list[dict[str, Any]]:
        return list(self._read(self.captures_path, {}).values())

    def relations(self) -> list[CaptureRelation]:
        return [
            CaptureRelation.model_validate(item)
            for item in self._read(self.relations_path, {}).values()
        ]

    def relation(self, relation_id: str) -> CaptureRelation | None:
        item = self._read(self.relations_path, {}).get(relation_id)
        return CaptureRelation.model_validate(item) if item else None

    def pair(self, from_id: str, to_id: str) -> CaptureRelation | None:
        return next(
            (
                item
                for item in self.relations()
                if item.from_capture_id == from_id and item.to_capture_id == to_id
            ),
            None,
        )

    def save_relation(self, relation: CaptureRelation) -> CaptureRelation:
        with self._lock:
            records = self._read(self.relations_path, {})
            records[relation.relation_id] = relation.model_dump(
                mode="json", by_alias=True
            )
            self._write(self.relations_path, records)
        return relation

    def enqueue(self, capture_id: str, code: str) -> None:
        with self._lock:
            jobs = self._read(self.jobs_path, {})
            prior = jobs.get(capture_id, {})
            jobs[capture_id] = {
                "jobId": prior.get("jobId", f"relation_job_{uuid4().hex}"),
                "captureId": capture_id,
                "jobType": "find_excerpt_session",
                "retryCount": int(prior.get("retryCount", 0)) + 1,
                "lastErrorCode": code,
                "updatedAt": _now().isoformat(),
            }
            self._write(self.jobs_path, jobs)

    @staticmethod
    def _read(path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CaptureRelationError(
                "RELATION_INDEX_READ_FAILED", str(error)
            ) from error

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise CaptureRelationError(
                "RELATION_INDEX_WRITE_FAILED", str(error)
            ) from error


class CaptureRelationMatcher:
    ELIGIBLE_ROLES: ClassVar[set[str]] = {"assistant", "tool", "system_summary"}

    def __init__(self, policy: MatchingPolicy | None = None) -> None:
        self.policy = policy or MatchingPolicy()

    def candidates(
        self, excerpt: dict[str, Any], sessions: Iterable[dict[str, Any]]
    ) -> list[MatchCandidate]:
        narrowed = [item for item in sessions if self._eligible_pair(excerpt, item)]
        exact = [
            candidate for item in narrowed if (candidate := self._exact(excerpt, item))
        ]
        if exact:
            return sorted(exact, key=lambda item: (-item.score, item.target_capture_id))
        if len(narrowed) > self.policy.max_substring_candidate_sessions:
            return []
        partial = [
            candidate
            for item in narrowed
            if (candidate := self._partial_or_group(excerpt, item))
        ]
        return sorted(partial, key=lambda item: (-item.score, item.target_capture_id))

    def pair_matches(self, excerpt: dict[str, Any], session: dict[str, Any]) -> bool:
        return bool(
            self._exact(excerpt, session) or self._partial_or_group(excerpt, session)
        )

    def _eligible_pair(self, excerpt: dict[str, Any], session: dict[str, Any]) -> bool:
        if not (
            excerpt.get("sourceType") == "codex"
            and excerpt.get("captureType") == "clipboard_item"
            and excerpt.get("captureDevice") == "android"
            and session.get("sourceType") == "codex"
            and session.get("captureType") == "development_session"
            and session.get("captureDevice") == "windows"
        ):
            return False
        left_project = excerpt.get("projectId")
        right_project = session.get("projectId")
        if left_project and right_project and left_project != right_project:
            return False
        delta = self._session_delta(excerpt, session)
        return delta is None or delta <= self.policy.window_hours * 3600

    def _exact(
        self, excerpt: dict[str, Any], session: dict[str, Any]
    ) -> MatchCandidate | None:
        digest = excerpt.get("contentHash")
        for message in self._messages(session):
            if digest and digest == message.get("contentHash"):
                return self._candidate(
                    excerpt,
                    session,
                    [message],
                    self.policy.exact_score,
                    "exact_message_hash",
                    1.0,
                )
        return None

    def _partial_or_group(
        self, excerpt: dict[str, Any], session: dict[str, Any]
    ) -> MatchCandidate | None:
        content = str(excerpt.get("normalizedContent") or "")
        if len(content) < self.policy.minimum_substring_chars:
            return None
        best: MatchCandidate | None = None
        messages = self._messages(session)
        for message in messages:
            ratio = _containment_ratio(
                content, str(message.get("normalizedContent") or "")
            )
            if ratio >= self.policy.minimum_substring_ratio:
                base = (
                    self.policy.substring_95_score
                    if ratio >= 0.95
                    else self.policy.substring_80_score
                )
                candidate = self._candidate(
                    excerpt, session, [message], base, "substring_match", ratio
                )
                if best is None or candidate.score > best.score:
                    best = candidate
        for size in range(2, self.policy.max_contiguous_messages + 1):
            for offset in range(len(messages) - size + 1):
                group = messages[offset : offset + size]
                combined = "\n".join(
                    str(item.get("normalizedContent") or "") for item in group
                )
                ratio = _containment_ratio(content, combined)
                if ratio < self.policy.minimum_substring_ratio:
                    continue
                candidate = self._candidate(
                    excerpt,
                    session,
                    group,
                    self.policy.contiguous_score,
                    "contiguous_message_group",
                    ratio,
                )
                if best is None or candidate.score > best.score:
                    best = candidate
        return best

    def _candidate(
        self,
        excerpt: dict[str, Any],
        session: dict[str, Any],
        messages: list[dict[str, Any]],
        base: int,
        method: str,
        ratio: float,
    ) -> MatchCandidate:
        same_project = bool(
            excerpt.get("projectId")
            and excerpt.get("projectId") == session.get("projectId")
        )
        delta = self._message_delta(excerpt, messages) or self._session_delta(
            excerpt, session
        )
        score = (
            base
            + (self.policy.same_project_score if same_project else 0)
            + _time_score(delta)
        )
        if _client_family(excerpt) == _client_family(session) == "codex":
            score += self.policy.same_client_score
        ids = [
            str(item.get("messageId") or item.get("sourceMessageId") or "")
            for item in messages
        ]
        evidence = RelationEvidence(
            clipboardContentHash=excerpt["contentHash"],
            matchedMessageId=ids[0] if len(ids) == 1 else None,
            matchedMessageIds=[item for item in ids if item],
            matchedContentHash=(
                messages[0].get("contentHash")
                if len(messages) == 1
                else _hash(
                    "\n".join(
                        str(item.get("normalizedContent") or "") for item in messages
                    )
                )
            ),
            matchRatio=round(ratio, 4),
            timeDeltaSeconds=delta,
            sameProject=same_project if excerpt.get("projectId") else None,
            targetRevision=int(session.get("revision", 1)),
        )
        return MatchCandidate(
            session["captureId"],
            str(session.get("title") or session["captureId"]),
            score,
            method,
            evidence,
        )

    def _messages(self, session: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            item
            for item in session.get("messages", [])
            if item.get("role") in self.ELIGIBLE_ROLES
        ]

    @staticmethod
    def _message_delta(
        excerpt: dict[str, Any], messages: list[dict[str, Any]]
    ) -> int | None:
        times = [_parse_time(item.get("createdAt")) for item in messages]
        source = _parse_time(excerpt.get("capturedAt"))
        valid = [
            abs(int((source - value).total_seconds()))
            for value in times
            if source and value
        ]
        return min(valid) if valid else None

    @staticmethod
    def _session_delta(excerpt: dict[str, Any], session: dict[str, Any]) -> int | None:
        source = _parse_time(excerpt.get("capturedAt"))
        if source is None:
            return None
        values = [
            _parse_time(session.get("startedAt")),
            _parse_time(session.get("endedAt")),
        ]
        valid = [
            abs(int((source - value).total_seconds())) for value in values if value
        ]
        return min(valid) if valid else None


class CaptureRelationService:
    def __init__(
        self,
        repository: CaptureRelationRepository,
        policy: MatchingPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.policy = policy or MatchingPolicy()
        self.matcher = CaptureRelationMatcher(self.policy)

    def record_capture(self, envelope: Any, result: Any) -> list[CaptureRelation]:
        record = self._record(envelope, result)
        self.repository.upsert_capture(record)
        try:
            if record["captureType"] == "development_session":
                self.revalidate(record["captureId"])
                created: list[CaptureRelation] = []
                for excerpt in self._excerpts():
                    created.extend(self.find_candidates(excerpt["captureId"]))
                return created
            return self.find_candidates(record["captureId"])
        except Exception as error:
            code = getattr(error, "code", "RELATION_MATCH_FAILED")
            self.repository.enqueue(record["captureId"], str(code))
            raise

    def find_candidates(
        self, capture_id: str, *, reconsider_rejected: bool = False
    ) -> list[CaptureRelation]:
        excerpt = self._required_capture(capture_id)
        if excerpt.get("captureType") != "clipboard_item":
            raise CaptureRelationError(
                "RELATION_TARGET_INVALID", "candidate source must be a clipboard item"
            )
        candidates = self.matcher.candidates(excerpt, self._sessions())
        if not candidates:
            return []
        top = candidates[0].score
        ambiguous = sum(candidate.score == top for candidate in candidates) > 1
        relations: list[CaptureRelation] = []
        for candidate in candidates:
            prior = self.repository.pair(capture_id, candidate.target_capture_id)
            if (
                prior
                and prior.status == RelationStatus.REJECTED
                and not reconsider_rejected
            ):
                continue
            if (
                prior
                and prior.created_by == "user"
                and prior.status == RelationStatus.CONFIRMED
            ):
                relations.append(prior)
                continue
            if (
                prior
                and prior.status == RelationStatus.REMOVED
                and not reconsider_rejected
            ):
                continue
            confidence = (
                RelationConfidence.HIGH
                if candidate.score >= self.policy.confirmed_score
                else RelationConfidence.MEDIUM
            )
            status = (
                RelationStatus.CONFIRMED
                if confidence == RelationConfidence.HIGH
                and not ambiguous
                and candidate.score == top
                else RelationStatus.SUGGESTED
            )
            now = _now()
            relation = CaptureRelation(
                relationId=prior.relation_id if prior else f"rel_{uuid4().hex}",
                fromCaptureId=capture_id,
                toCaptureId=candidate.target_capture_id,
                status=status,
                confidence=confidence,
                score=candidate.score,
                matchMethod=candidate.method,
                evidence=candidate.evidence,
                createdAt=prior.created_at if prior else now,
                updatedAt=now,
                createdBy="system",
                metadata=prior.metadata if prior else {},
            )
            if candidate.score >= self.policy.suggested_score:
                relations.append(self.repository.save_relation(relation))
        return relations

    def create_manual(self, from_id: str, to_id: str) -> CaptureRelation:
        excerpt = self._required_capture(from_id)
        session = self._required_capture(to_id)
        if not (
            excerpt.get("sourceType") == "codex"
            and excerpt.get("captureType") == "clipboard_item"
            and excerpt.get("captureDevice") == "android"
            and session.get("sourceType") == "codex"
            and session.get("captureType") == "development_session"
            and session.get("captureDevice") == "windows"
        ):
            raise CaptureRelationError(
                "INVALID_RELATION_DIRECTION",
                "excerpt_of must point from Android Codex clipboard "
                "to Windows Codex session",
            )
        prior = self.repository.pair(from_id, to_id)
        now = _now()
        evidence = RelationEvidence(
            clipboardContentHash=excerpt["contentHash"],
            targetRevision=int(session.get("revision", 1)),
        )
        return self.repository.save_relation(
            CaptureRelation(
                relationId=prior.relation_id if prior else f"rel_{uuid4().hex}",
                fromCaptureId=from_id,
                toCaptureId=to_id,
                status=RelationStatus.CONFIRMED,
                confidence=RelationConfidence.HIGH,
                score=self.policy.confirmed_score,
                matchMethod="manual",
                evidence=evidence,
                createdAt=prior.created_at if prior else now,
                updatedAt=now,
                createdBy="user",
                metadata={},
            )
        )

    def transition(
        self, relation_id: str, target: RelationStatus, *, reason: str | None = None
    ) -> CaptureRelation:
        relation = self._required_relation(relation_id)
        allowed = {
            RelationStatus.CONFIRMED: {RelationStatus.SUGGESTED, RelationStatus.STALE},
            RelationStatus.REJECTED: {
                RelationStatus.SUGGESTED,
                RelationStatus.CONFIRMED,
                RelationStatus.STALE,
            },
            RelationStatus.REMOVED: {RelationStatus.CONFIRMED, RelationStatus.STALE},
        }
        if relation.status not in allowed.get(target, set()):
            raise CaptureRelationError(
                "INVALID_RELATION_STATUS",
                f"cannot change {relation.status} to {target}",
            )
        metadata = dict(relation.metadata)
        if target == RelationStatus.REJECTED and reason:
            metadata["rejectionReason"] = reason
        return self.repository.save_relation(
            relation.model_copy(
                update={
                    "status": target,
                    "updated_at": _now(),
                    "created_by": "user",
                    "metadata": metadata,
                }
            )
        )

    def relations_for(
        self, capture_id: str, *, status: str | None = None, direction: str = "both"
    ) -> list[CaptureRelation]:
        result = []
        for item in self.repository.relations():
            inbound = item.to_capture_id == capture_id
            outbound = item.from_capture_id == capture_id
            if not (
                (direction in {"both", "in"} and inbound)
                or (direction in {"both", "out"} and outbound)
            ):
                continue
            if status and item.status.value != status:
                continue
            result.append(item)
        return result

    def revalidate(self, session_id: str) -> list[CaptureRelation]:
        session = self._required_capture(session_id)
        changed = []
        for relation in self.relations_for(session_id, direction="in"):
            if relation.status not in {RelationStatus.CONFIRMED, RelationStatus.STALE}:
                continue
            excerpt = self._required_capture(relation.from_capture_id)
            valid = relation.match_method == "manual" or self.matcher.pair_matches(
                excerpt, session
            )
            target = RelationStatus.CONFIRMED if valid else RelationStatus.STALE
            if relation.status != target or relation.evidence.target_revision != int(
                session.get("revision", 1)
            ):
                evidence = relation.evidence.model_copy(
                    update={"target_revision": int(session.get("revision", 1))}
                )
                changed.append(
                    self.repository.save_relation(
                        relation.model_copy(
                            update={
                                "status": target,
                                "evidence": evidence,
                                "updated_at": _now(),
                            }
                        )
                    )
                )
        return changed

    def backfill(
        self,
        *,
        dry_run: bool = False,
        limit: int | None = None,
        project_id: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        auto_confirm: bool = True,
    ) -> dict[str, int]:
        excerpts = [
            item
            for item in self._excerpts()
            if (not project_id or item.get("projectId") == project_id)
            and _within_dates(item.get("capturedAt"), from_date, to_date)
        ]
        if limit is not None:
            excerpts = excerpts[:limit]
        counts = {
            "androidCodexExcerpts": len(excerpts),
            "windowsCodexSessions": len(self._sessions()),
            "high": 0,
            "medium": 0,
            "unmatched": 0,
            "duplicates": 0,
        }
        for excerpt in excerpts:
            candidates = self.matcher.candidates(excerpt, self._sessions())
            if not candidates:
                counts["unmatched"] += 1
                continue
            top = candidates[0].score
            ambiguous = sum(item.score == top for item in candidates) > 1
            for candidate in candidates:
                if self.repository.pair(
                    excerpt["captureId"], candidate.target_capture_id
                ):
                    counts["duplicates"] += 1
                if candidate.score >= self.policy.confirmed_score and not ambiguous:
                    counts["high"] += 1
                elif candidate.score >= self.policy.suggested_score:
                    counts["medium"] += 1
            if not dry_run:
                relations = self.find_candidates(excerpt["captureId"])
                if not auto_confirm:
                    for relation in relations:
                        if relation.status == RelationStatus.CONFIRMED:
                            self.repository.save_relation(
                                relation.model_copy(
                                    update={"status": RelationStatus.SUGGESTED}
                                )
                            )
        return counts

    def _record(self, envelope: Any, result: Any) -> dict[str, Any]:
        payload = envelope.payload
        record = {
            "captureId": envelope.capture_id,
            "sourceType": envelope.source_type.value,
            "captureType": envelope.capture_type.value,
            "captureDevice": envelope.capture_device.value,
            "capturedAt": envelope.captured_at.isoformat(),
            "projectId": envelope.project_id,
            "sourceApp": envelope.metadata.get("sourceApp"),
            "documentId": result.document_id,
            "documentPath": result.document_path,
            "revision": result.revision,
        }
        if record["captureType"] == "clipboard_item":
            from autoknowledge_lite.capture_api import (
                normalize_capture_text,
                server_content_hash,
            )

            content = normalize_capture_text(str(payload.get("content") or ""))
            record.update(
                {
                    "contentHash": server_content_hash(content),
                    "normalizedContent": content,
                    "title": payload.get("title"),
                }
            )
        else:
            from autoknowledge_lite.capture_api import (
                normalize_capture_text,
                server_content_hash,
            )

            messages = []
            for sequence, item in enumerate(payload.get("messages", []), 1):
                content = normalize_capture_text(str(item.get("content") or ""))
                if not content:
                    continue
                messages.append(
                    {
                        "messageId": item.get("sourceMessageId")
                        or item.get("messageId")
                        or f"msg_{sequence}",
                        "role": item.get("role"),
                        "messageType": item.get("messageType"),
                        "contentHash": server_content_hash(content),
                        "normalizedContent": content,
                        "createdAt": item.get("createdAt"),
                    }
                )
            record.update(
                {
                    "contentHash": "",
                    "title": payload.get("title"),
                    "startedAt": payload.get("startedAt"),
                    "endedAt": payload.get("endedAt"),
                    "clientType": payload.get("clientType"),
                    "messages": messages,
                }
            )
        return record

    def _sessions(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.repository.captures()
            if item.get("captureType") == "development_session"
        ]

    def _excerpts(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.repository.captures()
            if item.get("captureType") == "clipboard_item"
        ]

    def _required_capture(self, capture_id: str) -> dict[str, Any]:
        item = self.repository.capture(capture_id)
        if not item:
            raise CaptureRelationError("CAPTURE_NOT_FOUND", capture_id)
        return item

    def _required_relation(self, relation_id: str) -> CaptureRelation:
        item = self.repository.relation(relation_id)
        if not item:
            raise CaptureRelationError("RELATION_NOT_FOUND", relation_id)
        return item


def ingest_existing_captures(
    service: CaptureRelationService,
    *,
    capture_index_path: Path,
    vault_dir: Path,
    codex_home: Path | None = None,
) -> dict[str, int]:
    """Build matching metadata for captures saved before the relation feature."""

    imported = {"clipboardItems": 0, "developmentSessions": 0, "skipped": 0}
    index = CaptureRelationRepository._read(capture_index_path, {})
    envelopes: dict[str, dict[str, Any]] = {}
    if codex_home and (codex_home / "sessions").is_dir():
        for path in (codex_home / "sessions").glob("*/envelope.json"):
            envelope = CaptureRelationRepository._read(path, {})
            if envelope.get("captureId"):
                envelopes[str(envelope["captureId"])] = envelope
    for capture_id, item in index.items():
        if service.repository.capture(capture_id):
            continue
        capture_type = item.get("captureType")
        if capture_type == "development_session" and capture_id in envelopes:
            try:
                from autoknowledge_lite.capture_api import (
                    CaptureEnvelope,
                    CaptureResult,
                )

                envelope = CaptureEnvelope.model_validate(envelopes[capture_id])
                result = CaptureResult.model_validate(item["response"])
                service.repository.upsert_capture(service._record(envelope, result))
                imported["developmentSessions"] += 1
            except Exception:  # noqa: BLE001 - corrupt legacy entries are isolated.
                imported["skipped"] += 1
            continue
        if capture_type != "clipboard_item":
            imported["skipped"] += 1
            continue
        document_path = vault_dir / str(item.get("documentPath") or "")
        try:
            markdown = document_path.read_text(encoding="utf-8")
            metadata, content = _parse_clipboard_markdown(markdown)
            normalized = _normalize_for_ingest(content)
            if not normalized:
                raise ValueError("clipboard body is empty")
            service.repository.upsert_capture(
                {
                    "captureId": capture_id,
                    "sourceType": metadata.get("source_type"),
                    "captureType": "clipboard_item",
                    "captureDevice": metadata.get("capture_device"),
                    "capturedAt": metadata.get("captured_at") or item.get("createdAt"),
                    "projectId": metadata.get("project_id"),
                    "sourceApp": metadata.get("source_app"),
                    "documentId": item.get("documentId"),
                    "documentPath": item.get("documentPath"),
                    "revision": int(item.get("response", {}).get("revision", 1)),
                    "contentHash": _hash(normalized),
                    "normalizedContent": normalized,
                    "title": metadata.get("title"),
                }
            )
            imported["clipboardItems"] += 1
        except (OSError, ValueError, json.JSONDecodeError):
            imported["skipped"] += 1
    return imported


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _containment_ratio(left: str, right: str) -> float:
    if not left or not right or (left not in right and right not in left):
        return 0.0
    return min(len(left), len(right)) / max(len(left), len(right))


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _within_dates(
    value: Any, from_date: datetime | None, to_date: datetime | None
) -> bool:
    parsed = _parse_time(value)
    if parsed is None:
        return from_date is None and to_date is None
    comparable = parsed.astimezone(UTC)
    if from_date is not None and comparable < from_date.astimezone(UTC):
        return False
    return not (to_date is not None and comparable > to_date.astimezone(UTC))


def _time_score(delta: int | None) -> int:
    if delta is None:
        return 0
    if delta <= 5 * 60:
        return 20
    if delta <= 30 * 60:
        return 15
    if delta <= 2 * 60 * 60:
        return 8
    return 0


def _client_family(record: dict[str, Any]) -> str:
    value = str(record.get("sourceApp") or record.get("clientType") or "").lower()
    return "codex" if "codex" in value else value


def _parse_clipboard_markdown(markdown: str) -> tuple[dict[str, Any], str]:
    lines = markdown.splitlines()
    metadata: dict[str, Any] = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, separator, value = line.partition(":")
            if separator:
                try:
                    metadata[key.strip()] = json.loads(value.strip())
                except json.JSONDecodeError:
                    metadata[key.strip()] = value.strip()
    marker = "## 원문"
    if marker not in lines:
        raise ValueError("clipboard body marker not found")
    start = lines.index(marker) + 1
    end = lines.index("## 연결", start) if "## 연결" in lines[start:] else len(lines)
    return metadata, "\n".join(lines[start:end]).strip()


def _normalize_for_ingest(value: str) -> str:
    source = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    return source


class ManualRelationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    relation_type: str = Field(default="excerpt_of", alias="relationType")
    from_capture_id: str = Field(alias="fromCaptureId", min_length=1, max_length=200)
    to_capture_id: str = Field(alias="toCaptureId", min_length=1, max_length=200)


class RejectRelationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    rejection_reason: str | None = Field(
        default=None, alias="rejectionReason", max_length=100
    )


def install_relation_api(application: Any, service: CaptureRelationService) -> None:
    """Install Capture relation routes without exposing stored source text."""

    from fastapi import Query
    from fastapi.responses import JSONResponse

    def failure(error: CaptureRelationError) -> JSONResponse:
        status_code = (
            404 if error.code in {"CAPTURE_NOT_FOUND", "RELATION_NOT_FOUND"} else 409
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": error.code, "message": str(error)}},
        )

    @application.get(
        "/api/v1/captures/{capture_id}/relation-candidates", response_model=None
    )
    def relation_candidates(capture_id: str) -> dict[str, Any] | JSONResponse:
        try:
            if service.repository.capture(capture_id) is None:
                raise CaptureRelationError("CAPTURE_NOT_FOUND", capture_id)
            relations = [
                item
                for item in service.relations_for(capture_id, direction="out")
                if item.status == RelationStatus.SUGGESTED
            ]
            return {
                "captureId": capture_id,
                "candidates": [
                    _candidate_response(
                        item, service.repository.capture(item.to_capture_id)
                    )
                    for item in relations
                ],
            }
        except CaptureRelationError as error:
            return failure(error)

    @application.post(
        "/api/v1/captures/{capture_id}/relation-candidates/search", response_model=None
    )
    def search_relation_candidates(
        capture_id: str, request: Request
    ) -> dict[str, Any] | JSONResponse:
        if response := _authorize_optional(request):
            return response
        try:
            relations = service.find_candidates(capture_id)
            return {
                "captureId": capture_id,
                "candidates": [
                    _candidate_response(
                        item, service.repository.capture(item.to_capture_id)
                    )
                    for item in relations
                ],
            }
        except CaptureRelationError as error:
            return failure(error)

    @application.get("/api/v1/captures/{capture_id}/relations", response_model=None)
    def capture_relations(
        capture_id: str,
        relation_type: str = Query("excerpt_of", alias="relationType"),
        relation_status: str | None = Query(None, alias="status"),
        direction: str = Query("both", pattern="^(both|in|out)$"),
    ) -> dict[str, Any] | JSONResponse:
        if relation_type != "excerpt_of":
            return failure(CaptureRelationError("INVALID_RELATION_TYPE", relation_type))
        if service.repository.capture(capture_id) is None:
            return failure(CaptureRelationError("CAPTURE_NOT_FOUND", capture_id))
        return {
            "captureId": capture_id,
            "relations": [
                item.model_dump(mode="json", by_alias=True)
                for item in service.relations_for(
                    capture_id, status=relation_status, direction=direction
                )
            ],
        }

    @application.get("/api/v1/captures/{session_id}/excerpts", response_model=None)
    def session_excerpts(session_id: str) -> dict[str, Any] | JSONResponse:
        session = service.repository.capture(session_id)
        if not session:
            return failure(CaptureRelationError("CAPTURE_NOT_FOUND", session_id))
        if session.get("captureType") != "development_session":
            return failure(CaptureRelationError("RELATION_TARGET_INVALID", session_id))
        items = []
        for relation in service.relations_for(session_id, direction="in"):
            excerpt = service.repository.capture(relation.from_capture_id) or {}
            items.append(
                {
                    "captureId": relation.from_capture_id,
                    "title": excerpt.get("title"),
                    "capturedAt": excerpt.get("capturedAt"),
                    "relationStatus": relation.status.value,
                    "confidence": relation.confidence.value,
                    "matchedMessageId": relation.evidence.matched_message_id,
                }
            )
        return {"sessionCaptureId": session_id, "items": items}

    @application.post("/api/v1/capture-relations", response_model=None)
    def create_relation(
        payload: ManualRelationRequest, request: Request
    ) -> CaptureRelation | JSONResponse:
        if response := _authorize_optional(request):
            return response
        if payload.relation_type != "excerpt_of":
            return failure(
                CaptureRelationError("INVALID_RELATION_TYPE", payload.relation_type)
            )
        try:
            return service.create_manual(payload.from_capture_id, payload.to_capture_id)
        except CaptureRelationError as error:
            return failure(error)

    @application.post(
        "/api/v1/capture-relations/{relation_id}/confirm", response_model=None
    )
    def confirm_relation(
        relation_id: str, request: Request
    ) -> CaptureRelation | JSONResponse:
        if response := _authorize_optional(request):
            return response
        try:
            return service.transition(relation_id, RelationStatus.CONFIRMED)
        except CaptureRelationError as error:
            return failure(error)

    @application.post(
        "/api/v1/capture-relations/{relation_id}/reject", response_model=None
    )
    def reject_relation(
        relation_id: str, payload: RejectRelationRequest, request: Request
    ) -> CaptureRelation | JSONResponse:
        if response := _authorize_optional(request):
            return response
        try:
            return service.transition(
                relation_id, RelationStatus.REJECTED, reason=payload.rejection_reason
            )
        except CaptureRelationError as error:
            return failure(error)

    @application.delete("/api/v1/capture-relations/{relation_id}", response_model=None)
    def remove_relation(
        relation_id: str, request: Request
    ) -> CaptureRelation | JSONResponse:
        if response := _authorize_optional(request):
            return response
        try:
            return service.transition(relation_id, RelationStatus.REMOVED)
        except CaptureRelationError as error:
            return failure(error)


def _candidate_response(
    relation: CaptureRelation, target: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "relationId": relation.relation_id,
        "targetCaptureId": relation.to_capture_id,
        "targetTitle": (target or {}).get("title"),
        "confidence": relation.confidence.value,
        "score": relation.score,
        "matchMethod": relation.match_method,
        "evidence": relation.evidence.model_dump(mode="json", by_alias=True),
        "status": relation.status.value,
    }


def _authorize_optional(request: Any) -> Any | None:
    """Require the control key when configured; never echo credentials."""

    configured = os.getenv("AUTOKNOWLEDGE_CONTROL_API_KEY", "").strip()
    if not configured:
        return None
    provided = request.headers.get("Authorization", "")
    expected = f"Bearer {configured}"
    if not hmac.compare_digest(provided, expected):
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Authentication is required.",
                }
            },
        )
    return None
