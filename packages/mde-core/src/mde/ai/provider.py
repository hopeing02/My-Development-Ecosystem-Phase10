from __future__ import annotations

from typing import Protocol

from mde.ai.models import AIRequest, AIResponse


class AIProvider(Protocol):
    name: str

    def execute(self, request: AIRequest) -> AIResponse:
        """Execute an AI request without mutating repository files."""
