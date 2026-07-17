from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mde.ai.artifacts import write_response_bundle
from mde.ai.models import AIRequest, AIResponse
from mde.ai.providers import (
    ClaudeProvider,
    GeminiProvider,
    LocalLLMProvider,
    MockAIProvider,
    OpenAIProvider,
)
from mde.ai.registry import AIProviderRegistry


class AIEngine:
    def __init__(self, registry: AIProviderRegistry | None = None) -> None:
        self.registry = registry or create_default_provider_registry()

    def execute(
        self,
        *,
        action: str,
        prompt: str,
        repository_root: Path,
        run_id: str,
        step_id: str,
        provider_name: str | None = None,
        task_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> tuple[AIResponse, Path]:
        selected = provider_name or os.environ.get("MDE_AI_PROVIDER", "mock")
        provider = self.registry.get(selected)
        request = AIRequest(
            action=action,  # type: ignore[arg-type]
            prompt=prompt,
            repository_root=repository_root,
            task_id=task_id,
            context=dict(context or {}),
        )
        response = provider.execute(request)
        manifest_path = write_response_bundle(
            response, repository_root, run_id=run_id, step_id=step_id
        )
        return response, manifest_path


def create_default_provider_registry() -> AIProviderRegistry:
    registry = AIProviderRegistry()
    registry.register(MockAIProvider())
    registry.register(OpenAIProvider())
    registry.register(ClaudeProvider())
    registry.register(GeminiProvider())
    registry.register(LocalLLMProvider())
    return registry
