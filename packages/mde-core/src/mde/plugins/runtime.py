from __future__ import annotations

from mde.plugins.builtin import AIWorkflowPlugin, CoreWorkflowPlugin, GitWorkflowPlugin, TestingWorkflowPlugin
from mde.plugins.manager import PluginManager
from mde.workflow.registry import CommandRegistry


def create_runtime_plugin_manager() -> PluginManager:
    return PluginManager(
        (
            CoreWorkflowPlugin(),
            AIWorkflowPlugin(),
            TestingWorkflowPlugin(),
            GitWorkflowPlugin(),
        )
    )


def create_runtime_registry() -> CommandRegistry:
    return create_runtime_plugin_manager().register_all(CommandRegistry())
