from __future__ import annotations
from typing import Any
from mde.ai.errors import AIResponseValidationError
from mde.ai.models import AIRequest
from mde.ai.providers.base_http import BaseHTTPAIProvider, SYSTEM_PROMPT


class ClaudeProvider(BaseHTTPAIProvider):
    name = "claude"
    api_key_env = "ANTHROPIC_API_KEY"
    model_env = "MDE_CLAUDE_MODEL"
    default_model = "claude-sonnet-4-6"

    def build_request(self, request: AIRequest, *, api_key: str, model: str):
        return (
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
            {
                "model": model,
                "max_tokens": 8192,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": self.user_prompt(request)}],
            },
        )

    def extract_text_and_usage(self, data: dict[str, Any]):
        chunks = [
            item.get("text", "")
            for item in data.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(chunk for chunk in chunks if chunk)
        if not text:
            raise AIResponseValidationError("Claude response contains no text.")
        return text, dict(data.get("usage") or {})
