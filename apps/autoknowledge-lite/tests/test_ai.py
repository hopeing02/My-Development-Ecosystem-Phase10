from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from autoknowledge_lite.ai import (
    AnalysisError,
    ClaudeKnowledgeAnalyzer,
    DeterministicKnowledgeAnalyzer,
    OpenAIKnowledgeAnalyzer,
    analyzer_from_environment,
)
from autoknowledge_lite.models import ShareRecord


def share_record() -> ShareRecord:
    return ShareRecord(
        job_id="00000000-0000-0000-0000-000000000001",
        received_at=datetime.now(timezone.utc),
        title="Useful article",
        content="First point. Second point.",
    )


def test_openai_analyzer_uses_responses_api() -> None:
    calls = []

    class Responses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                output_text='{"summary":"Summary","key_points":["Point"],"tags":["tag"]}'
            )

    client = SimpleNamespace(responses=Responses())
    analyzer = OpenAIKnowledgeAnalyzer(client=client, model="test-openai")

    result = analyzer.analyze(share_record())

    assert result.provider == "openai:test-openai"
    assert result.summary == "Summary"
    assert calls[0]["model"] == "test-openai"


def test_openai_analyzer_defers_sdk_import_until_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "openai", None)

    analyzer = OpenAIKnowledgeAnalyzer(model="test-openai")

    assert analyzer.client is None
    with pytest.raises(AnalysisError, match="OpenAI SDK is not installed"):
        analyzer.analyze(share_record())


def test_claude_analyzer_uses_messages_api() -> None:
    calls = []

    class Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            text = '```json\n{"summary":"Summary","key_points":[],"tags":[]}\n```'
            return SimpleNamespace(content=[SimpleNamespace(text=text)])

    client = SimpleNamespace(messages=Messages())
    analyzer = ClaudeKnowledgeAnalyzer(client=client, model="test-claude")

    result = analyzer.analyze(share_record())

    assert result.provider == "claude:test-claude"
    assert result.summary == "Summary"
    assert calls[0]["model"] == "test-claude"


def test_claude_analyzer_defers_sdk_import_until_analysis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "anthropic", None)

    analyzer = ClaudeKnowledgeAnalyzer(model="test-claude")

    assert analyzer.client is None
    with pytest.raises(AnalysisError, match="Anthropic SDK is not installed"):
        analyzer.analyze(share_record())


def test_provider_selection_defaults_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_AI_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert isinstance(analyzer_from_environment(), DeterministicKnowledgeAnalyzer)


def test_provider_selection_prefers_openai_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUTOKNOWLEDGE_AI_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert isinstance(analyzer_from_environment(), OpenAIKnowledgeAnalyzer)


def test_explicit_local_provider_overrides_available_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_AI_PROVIDER", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    assert isinstance(analyzer_from_environment(), DeterministicKnowledgeAnalyzer)


def test_provider_selection_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTOKNOWLEDGE_AI_PROVIDER", "unknown")

    with pytest.raises(AnalysisError, match="Unsupported AI provider"):
        analyzer_from_environment()


def test_openai_analyzer_hides_provider_failure() -> None:
    class Responses:
        def create(self, **kwargs):
            raise RuntimeError("secret provider response")

    client = SimpleNamespace(responses=Responses())

    with pytest.raises(AnalysisError, match="OpenAI analysis request failed"):
        OpenAIKnowledgeAnalyzer(client=client).analyze(share_record())
