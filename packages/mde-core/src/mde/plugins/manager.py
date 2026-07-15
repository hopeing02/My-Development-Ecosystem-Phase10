from __future__ import annotations

from mde.plugins.base import Plugin
from mde.workflow.registry import CommandRegistry


class PluginManager:
    def __init__(self, plugins: tuple[Plugin, ...] = ()) -> None:
        self._plugins: list[Plugin] = []
        for plugin in plugins:
            self.add(plugin)

    def add(self, plugin: Plugin) -> None:
        if any(existing.name == plugin.name for existing in self._plugins):
            raise ValueError(f"Plugin '{plugin.name}' is already loaded.")
        self._plugins.append(plugin)

    def register_all(self, registry: CommandRegistry) -> CommandRegistry:
        for plugin in self._plugins:
            plugin.register(registry)
        return registry

    def names(self) -> tuple[str, ...]:
        return tuple(plugin.name for plugin in self._plugins)
