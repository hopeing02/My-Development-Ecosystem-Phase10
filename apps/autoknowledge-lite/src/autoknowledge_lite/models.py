"""Validated API contracts for AutoKnowledge Lite."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class KnowledgeAnalysis(BaseModel):
    """Structured analysis produced for a shared item."""

    summary: str
    key_points: list[str]
    tags: list[str]
    provider: str


class ShareRequest(BaseModel):
    """Content shared by a mobile client or API caller."""

    content: str = Field(min_length=1, max_length=100_000)
    title: str | None = Field(default=None, max_length=200)
    source_url: AnyHttpUrl | None = None
    shared_at: datetime | None = None

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content must not be blank")
        return normalized

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ShareRecord(BaseModel):
    """Persisted representation of an accepted share request."""

    job_id: str
    status: Literal["queued", "processed"] = "queued"
    received_at: datetime
    content: str
    title: str | None = None
    source_url: str | None = None
    shared_at: datetime | None = None
    processed_at: datetime | None = None
    analysis: KnowledgeAnalysis | None = None
    markdown: str | None = None
    note_path: str | None = None


class ShareAccepted(BaseModel):
    """Response returned after durable local acceptance."""

    job_id: str
    status: Literal["queued"] = "queued"
    received_at: datetime


class ProcessRequest(BaseModel):
    """Request to analyze one previously accepted share job."""

    job_id: UUID


class ProcessedShare(BaseModel):
    """Response returned after analysis is persisted."""

    job_id: str
    status: Literal["processed"] = "processed"
    processed_at: datetime
    analysis: KnowledgeAnalysis


class MarkdownRequest(BaseModel):
    job_id: UUID


class MarkdownResult(BaseModel):
    job_id: str
    markdown: str
    note_path: str


class StatusResponse(BaseModel):
    """Public service status contract."""

    service: Literal["autoknowledge-lite"] = "autoknowledge-lite"
    status: Literal["ok"] = "ok"
    version: str
