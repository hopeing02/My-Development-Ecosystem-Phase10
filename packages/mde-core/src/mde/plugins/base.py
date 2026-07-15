from __future__ import annotations

from typing import Protocol

from mde.workflow.registry import CommandRegistry


class Plugin(Protocol):
    """A plugin that contributes workflow command handlers."""

    name: str

    def register(self, registry: CommandRegistry) -> None:
        """Register command handlers in the supplied registry."""
