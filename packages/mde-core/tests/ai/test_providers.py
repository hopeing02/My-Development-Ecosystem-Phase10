from pathlib import Path
import json

import pytest

from mde.ai.errors import (
    AIConfigurationError,
    AIResponseValidationError,
    AITransportError,
)
from mde.ai.models import AIRequest
from mde.ai.providers.claude import ClaudeProvider
from mde.ai.providers.gemini import GeminiProvider
from mde.ai.providers.local import LocalLLMProvider
from mde.ai.providers.openai import OpenAIProvider
from mde.ai.transport import HTTPResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post_json(self, url, *, headers, payload, timeout):
        self.calls.append((url, headers, payload, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return HTTPResponse(status=200, data=response, headers={})


def request(tmp_path: Path):
    return AIRequest(action="generate", prompt="create file", repository_root=tmp_path)


@pytest.mark.parametrize(
    ("provider", "response"),
    [
        (
            OpenAIProvider,
            {
                "output_text": '{"summary":"ok","artifacts":[{"path":"a.txt","content":"A"}]}',
                "usage": {"input_tokens": 2, "output_tokens": 3},
            },
        ),
        (
            ClaudeProvider,
            {
                "content": [
                    {"type": "text", "text": '{"summary":"ok","artifacts":[]}'}
                ],
                "usage": {"input_tokens": 2, "output_tokens": 3},
            },
        ),
        (
            GeminiProvider,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"summary":"ok","artifacts":[]}'}]
                        }
                    }
                ],
                "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 3},
            },
        ),
        (
            LocalLLMProvider,
            {
                "choices": [
                    {"message": {"content": '{"summary":"ok","artifacts":[]}'}}
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 3},
            },
        ),
    ],
)
def test_provider_parses_structured_response(
    tmp_path: Path, provider, response, monkeypatch
):
    transport = FakeTransport([response])
    instance = provider(
        transport=transport, api_key="key", model="model", max_retries=0
    )
    if provider is LocalLLMProvider:
        monkeypatch.setenv("MDE_LOCAL_BASE_URL", "http://localhost/v1/chat/completions")
    result = instance.execute(request(tmp_path))
    assert result.summary == "ok"
    assert result.metadata["usage"]["total_tokens"] == 5
    assert result.metadata["attempts"] == 1


def test_provider_requires_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(AIConfigurationError, match="OPENAI_API_KEY"):
        OpenAIProvider(max_retries=0).execute(request(tmp_path))


@pytest.mark.parametrize("verdict", [None, False, "true", True])
def test_http_review_verdict_is_explicit_and_context_is_sent(
    tmp_path: Path, verdict
) -> None:
    transport = FakeTransport(
        [
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "summary": "review",
                                    "artifacts": [],
                                    "approved": verdict,
                                }
                            )
                        }
                    }
                ]
            }
        ]
    )
    provider = LocalLLMProvider(transport=transport, max_retries=0)
    review = AIRequest(
        action="review",
        prompt="review code",
        repository_root=tmp_path,
        context={"artifacts": [{"path": "example.py", "content": "print(42)"}]},
    )
    if type(verdict) is bool:
        assert provider.execute(review).metadata["approved"] is verdict
    else:
        with pytest.raises(AIResponseValidationError, match="boolean approved"):
            provider.execute(review)
    payload = transport.calls[0][2]
    assert "print(42)" in json.dumps(payload)


def test_provider_retries_transport_failure(tmp_path: Path):
    transport = FakeTransport(
        [
            AITransportError("temporary"),
            {"output_text": '{"summary":"recovered","artifacts":[]}'},
        ]
    )
    result = OpenAIProvider(
        transport=transport, api_key="key", model="model", max_retries=1, retry_delay=0
    ).execute(request(tmp_path))
    assert result.summary == "recovered"
    assert result.metadata["attempts"] == 2
    assert len(transport.calls) == 2


def test_invalid_artifact_document_is_rejected(tmp_path: Path):
    transport = FakeTransport([{"output_text": '{"summary":"","artifacts":[]}'}])
    with pytest.raises(AIResponseValidationError):
        OpenAIProvider(
            transport=transport, api_key="key", model="model", max_retries=0
        ).execute(request(tmp_path))
