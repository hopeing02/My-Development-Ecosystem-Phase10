from __future__ import annotations
from typing import Any
from mde.ai.errors import AIResponseValidationError
from mde.ai.models import AIRequest
from mde.ai.providers.base_http import BaseHTTPAIProvider, SYSTEM_PROMPT


class OpenAIProvider(BaseHTTPAIProvider):
    name = "openai"
    api_key_env = "OPENAI_API_KEY"
    model_env = "MDE_OPENAI_MODEL"
    default_model = "gpt-5-mini"

    def build_request(self, request: AIRequest, *, api_key: str, model: str):
        return (
            "https://api.openai.com/v1/responses",
            {"Authorization": f"Bearer {api_key}"},
            {
                "model": model,
                "instructions": SYSTEM_PROMPT,
                "input": self.user_prompt(request),
            },
        )

    def extract_text_and_usage(self, data: dict[str, Any]):
        text = data.get("output_text")
        if not isinstance(text, str):
            chunks = []
            for item in data.get("output", []):
                if isinstance(item, dict):
                    for content in item.get("content", []):
                        if isinstance(content, dict) and isinstance(
                            content.get("text"), str
                        ):
                            chunks.append(content["text"])
            text = "\n".join(chunks)
        if not text:
            raise AIResponseValidationError("OpenAI response contains no text.")
        return text, dict(data.get("usage") or {})
