from __future__ import annotations
from typing import Any
from urllib.parse import quote
from mde.ai.errors import AIResponseValidationError
from mde.ai.models import AIRequest
from mde.ai.providers.base_http import BaseHTTPAIProvider, SYSTEM_PROMPT


class GeminiProvider(BaseHTTPAIProvider):
    name = "gemini"
    api_key_env = "GEMINI_API_KEY"
    model_env = "MDE_GEMINI_MODEL"
    default_model = "gemini-2.5-flash"

    def build_request(self, request: AIRequest, *, api_key: str, model: str):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model)}:generateContent?key={quote(api_key)}"
        return (
            url,
            {},
            {
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [
                    {"role": "user", "parts": [{"text": self.user_prompt(request)}]}
                ],
            },
        )

    def extract_text_and_usage(self, data: dict[str, Any]):
        chunks = []
        for candidate in data.get("candidates", []):
            if isinstance(candidate, dict):
                content = candidate.get("content", {})
                if isinstance(content, dict):
                    for part in content.get("parts", []):
                        if isinstance(part, dict) and isinstance(part.get("text"), str):
                            chunks.append(part["text"])
        text = "\n".join(chunks)
        if not text:
            raise AIResponseValidationError("Gemini response contains no text.")
        return text, dict(data.get("usageMetadata") or {})
