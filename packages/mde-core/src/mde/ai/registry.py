from __future__ import annotations

from mde.ai.provider import AIProvider
from mde.exceptions import MDEError


class AIProviderNotFoundError(MDEError, LookupError):
    """Raised when a requested AI provider is not registered."""


class AIProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, AIProvider] = {}

    def register(self, provider: AIProvider, *, replace: bool = False) -> None:
        name = provider.name.strip().lower()
        if not name:
            raise ValueError("AI provider name must not be empty.")
        if name in self._providers and not replace:
            raise ValueError(f"AI provider '{name}' is already registered.")
        self._providers[name] = provider

    def get(self, name: str) -> AIProvider:
        normalized = name.strip().lower()
        try:
            return self._providers[normalized]
        except KeyError as error:
            available = ", ".join(self.names()) or "none"
            raise AIProviderNotFoundError(
                f"AI provider '{name}' is not registered. Available: {available}"
            ) from error

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))
