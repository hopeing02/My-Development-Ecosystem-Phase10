"""AI analysis boundary with an offline deterministic implementation."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from threading import Lock
from typing import Any, Protocol

from autoknowledge_lite.models import KnowledgeAnalysis, ShareRecord

WORD_PATTERN = re.compile(r"[0-9A-Za-z가-힣_-]{2,}")
SENTENCE_PATTERN = re.compile(r"(?<=[.!?。！？])\s+|\n+")
STOP_WORDS = {
    "about",
    "and",
    "from",
    "that",
    "the",
    "this",
    "with",
    "그리고",
    "대한",
    "에서",
    "으로",
    "하는",
}
SYSTEM_PROMPT = """Analyze shared knowledge and return only a JSON object with keys:
summary (string, at most 500 characters), key_points (array of up to 5 strings),
and tags (array of up to 5 short strings). Do not include Markdown fences."""


class AnalysisError(RuntimeError):
    """Raised when a configured analyzer cannot produce a valid result."""


class KnowledgeAnalyzer(Protocol):
    """Provider-neutral boundary for share-content analysis."""

    def analyze(self, record: ShareRecord) -> KnowledgeAnalysis: ...


class DeterministicKnowledgeAnalyzer:
    """Generate repeatable summaries and tags without an external AI service."""

    provider = "local-deterministic"

    def analyze(self, record: ShareRecord) -> KnowledgeAnalysis:
        sentences = [
            " ".join(sentence.split())
            for sentence in SENTENCE_PATTERN.split(record.content)
            if sentence.strip()
        ]
        if not sentences:
            raise AnalysisError("Shared content contains no analyzable text.")

        key_points = sentences[:3]
        summary = " ".join(key_points[:2])[:500].rstrip()
        tokens = WORD_PATTERN.findall(f"{record.title or ''} {record.content}".lower())
        counts = Counter(token for token in tokens if token not in STOP_WORDS)
        tags = [token for token, _ in counts.most_common(5)] or ["uncategorized"]
        return KnowledgeAnalysis(
            summary=summary,
            key_points=key_points,
            tags=tags,
            provider=self.provider,
        )


def _analysis_from_json(raw: str, provider: str) -> KnowledgeAnalysis:
    """Validate a provider JSON response without exposing its raw contents."""

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        payload["provider"] = provider
        return KnowledgeAnalysis.model_validate(payload)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise AnalysisError(f"{provider} returned an invalid analysis.") from error


class OpenAIKnowledgeAnalyzer:
    """Analyze content with the OpenAI Responses API."""

    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
        self.client = client
        self._client_lock = Lock()
        self.provider = f"openai:{self.model}"

    def _client(self) -> Any:
        """Create the provider client only when analysis is requested."""

        if self.client is None:
            with self._client_lock:
                if self.client is None:
                    try:
                        from openai import OpenAI
                    except ImportError as error:
                        raise AnalysisError(
                            "The OpenAI SDK is not installed."
                        ) from error
                    self.client = OpenAI(
                        timeout=_provider_timeout_seconds(),
                        max_retries=0,
                    )
        return self.client

    def analyze(self, record: ShareRecord) -> KnowledgeAnalysis:
        try:
            response = self._client().responses.create(
                model=self.model,
                instructions=SYSTEM_PROMPT,
                input=_content_prompt(record),
            )
            return _analysis_from_json(response.output_text, self.provider)
        except AnalysisError:
            raise
        except Exception as error:
            raise AnalysisError("OpenAI analysis request failed.") from error


class ClaudeKnowledgeAnalyzer:
    """Analyze content with the Anthropic Messages API."""

    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.client = client
        self._client_lock = Lock()
        self.provider = f"claude:{self.model}"

    def _client(self) -> Any:
        """Create the provider client only when analysis is requested."""

        if self.client is None:
            with self._client_lock:
                if self.client is None:
                    try:
                        from anthropic import Anthropic
                    except ImportError as error:
                        raise AnalysisError(
                            "The Anthropic SDK is not installed."
                        ) from error
                    self.client = Anthropic(
                        timeout=_provider_timeout_seconds(),
                        max_retries=0,
                    )
        return self.client

    def analyze(self, record: ShareRecord) -> KnowledgeAnalysis:
        try:
            message = self._client().messages.create(
                model=self.model,
                max_tokens=1200,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _content_prompt(record)}],
            )
            raw = "".join(
                block.text for block in message.content if hasattr(block, "text")
            )
            return _analysis_from_json(raw, self.provider)
        except AnalysisError:
            raise
        except Exception as error:
            raise AnalysisError("Claude analysis request failed.") from error


def analyzer_from_environment() -> KnowledgeAnalyzer:
    """Build the configured analyzer, preferring an available API key."""

    configured = os.getenv("AUTOKNOWLEDGE_AI_PROVIDER")
    provider = configured.strip().lower() if configured else _provider_from_api_keys()
    if provider == "local":
        return DeterministicKnowledgeAnalyzer()
    if provider == "openai":
        return OpenAIKnowledgeAnalyzer()
    if provider in {"anthropic", "claude"}:
        return ClaudeKnowledgeAnalyzer()
    raise AnalysisError(f"Unsupported AI provider: {provider}")


def _provider_from_api_keys() -> str:
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude"
    return "local"


def _provider_timeout_seconds() -> float:
    configured = os.getenv("AUTOKNOWLEDGE_AI_TIMEOUT_SECONDS", "30")
    try:
        timeout = float(configured)
    except ValueError as error:
        raise AnalysisError(
            "AUTOKNOWLEDGE_AI_TIMEOUT_SECONDS must be a number."
        ) from error
    if timeout <= 0:
        raise AnalysisError(
            "AUTOKNOWLEDGE_AI_TIMEOUT_SECONDS must be greater than zero."
        )
    return timeout


def _content_prompt(record: ShareRecord) -> str:
    title = record.title or "(untitled)"
    source = record.source_url or "(none)"
    return f"Title: {title}\nSource: {source}\n\nContent:\n{record.content}"
