from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any

from mde.ai.errors import AIConfigurationError, AITransportError
from mde.ai.models import AIRequest, AIResponse
from mde.ai.parsing import extract_json_object, parse_artifact_document
from mde.ai.transport import HTTPTransport, UrllibHTTPTransport
from mde.ai.usage import estimate_cost_usd, normalize_usage

SYSTEM_PROMPT = """You are the MDE AI engine. Return JSON only with this schema:\n{\"summary\": \"...\", \"artifacts\": [{\"path\": \"relative/path\", \"content\": \"...\", \"media_type\": \"text/plain\"}]}\nNever use absolute paths or parent traversal. For review/summarize, artifacts may be empty."""


class BaseHTTPAIProvider(ABC):
    name: str
    api_key_env: str
    model_env: str
    default_model: str

    def __init__(
        self,
        *,
        transport: HTTPTransport | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        retry_delay: float = 0.25,
    ) -> None:
        self.transport = transport or UrllibHTTPTransport()
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _setting(self, explicit: Any, env: str, default: Any) -> Any:
        return explicit if explicit is not None else os.environ.get(env, default)

    def _credentials(self) -> tuple[str, str, float, int]:
        key = str(self._setting(self.api_key, self.api_key_env, "")).strip()
        if not key:
            raise AIConfigurationError(
                f"Missing API key environment variable: {self.api_key_env}"
            )
        model = str(
            self._setting(self.model, self.model_env, self.default_model)
        ).strip()
        timeout = float(self._setting(self.timeout, "MDE_AI_TIMEOUT", 60))
        retries = int(self._setting(self.max_retries, "MDE_AI_MAX_RETRIES", 2))
        return key, model, timeout, max(0, retries)

    @abstractmethod
    def build_request(
        self, request: AIRequest, *, api_key: str, model: str
    ) -> tuple[str, dict[str, str], dict[str, Any]]: ...

    @abstractmethod
    def extract_text_and_usage(
        self, data: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]: ...

    def execute(self, request: AIRequest) -> AIResponse:
        api_key, model, timeout, retries = self._credentials()
        url, headers, payload = self.build_request(
            request, api_key=api_key, model=model
        )
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self.transport.post_json(
                    url, headers=headers, payload=payload, timeout=timeout
                )
                text, usage = self.extract_text_and_usage(response.data)
                document = extract_json_object(text)
                summary, artifacts = parse_artifact_document(document)
                return AIResponse(
                    provider=self.name,
                    action=request.action,
                    summary=summary,
                    artifacts=artifacts,
                    metadata={
                        "model": model,
                        "usage": normalize_usage(usage),
                        "cost_usd": estimate_cost_usd(self.name, model, usage),
                        "attempts": attempt + 1,
                    },
                )
            except AITransportError as error:
                last_error = error
                if attempt >= retries:
                    raise
                time.sleep(self.retry_delay * (2**attempt))
        assert last_error is not None
        raise last_error

    @staticmethod
    def user_prompt(request: AIRequest) -> str:
        return f"Action: {request.action}\nTask ID: {request.task_id or 'none'}\nPrompt:\n{request.prompt}"
