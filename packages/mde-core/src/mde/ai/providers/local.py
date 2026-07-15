from __future__ import annotations
import os
from typing import Any
from mde.ai.errors import AIConfigurationError, AIResponseValidationError
from mde.ai.models import AIRequest
from mde.ai.providers.base_http import BaseHTTPAIProvider, SYSTEM_PROMPT

class LocalLLMProvider(BaseHTTPAIProvider):
    name = "local"
    api_key_env = "MDE_LOCAL_API_KEY"
    model_env = "MDE_LOCAL_MODEL"
    default_model = "local-model"

    def _credentials(self):
        model = str(self._setting(self.model, self.model_env, self.default_model)).strip()
        timeout = float(self._setting(self.timeout, "MDE_AI_TIMEOUT", 60))
        retries = int(self._setting(self.max_retries, "MDE_AI_MAX_RETRIES", 2))
        return str(self.api_key or os.environ.get(self.api_key_env, "local")), model, timeout, max(0, retries)

    def build_request(self, request: AIRequest, *, api_key: str, model: str):
        url = os.environ.get("MDE_LOCAL_BASE_URL", "http://127.0.0.1:11434/v1/chat/completions")
        if not url.startswith(("http://", "https://")):
            raise AIConfigurationError("MDE_LOCAL_BASE_URL must be an HTTP(S) URL.")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key and api_key != "local" else {}
        return url, headers, {"model": model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": self.user_prompt(request)}], "temperature": 0}

    def extract_text_and_usage(self, data: dict[str, Any]):
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise AIResponseValidationError("Local LLM response contains no chat content.") from error
        if not isinstance(text, str) or not text:
            raise AIResponseValidationError("Local LLM response contains no text.")
        return text, dict(data.get("usage") or {})
