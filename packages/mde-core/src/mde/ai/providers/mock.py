from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mde.ai.models import AIArtifact, AIRequest, AIResponse


class MockAIProvider:
    """Deterministic provider used for local development and tests.

    Artifacts can be supplied through request.context['artifacts'] as a list of
    {'path': 'relative/path.txt', 'content': '...'} mappings.
    """

    name = "mock"

    def execute(self, request: AIRequest) -> AIResponse:
        raw_artifacts = request.context.get("artifacts", ())
        artifacts: list[AIArtifact] = []
        if isinstance(raw_artifacts, Sequence) and not isinstance(raw_artifacts, (str, bytes)):
            for item in raw_artifacts:
                if not isinstance(item, Mapping):
                    continue
                path = str(item.get("path", "")).strip()
                if not path:
                    continue
                artifacts.append(
                    AIArtifact(
                        path=path,
                        content=str(item.get("content", "")),
                        media_type=str(item.get("media_type", "text/plain")),
                    )
                )

        if request.action == "review":
            summary = "Mock review completed."
        elif request.action == "fix":
            summary = "Mock fix completed."
        else:
            summary = f"Mock {request.action} completed for: {request.prompt}"

        return AIResponse(
            provider=self.name,
            action=request.action,
            summary=summary,
            artifacts=tuple(artifacts),
            metadata={"deterministic": True},
        )
