import pytest

from mde.plugins.builtin import CoreWorkflowPlugin
from mde.plugins.manager import PluginManager
from mde.plugins.runtime import create_runtime_registry


def test_plugin_manager_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="already loaded"):
        PluginManager((CoreWorkflowPlugin(), CoreWorkflowPlugin()))


def test_runtime_registry_contains_real_boundary_commands() -> None:
    commands = create_runtime_registry().list_commands()
    assert "test.run" in commands
    assert "git.save" in commands
    assert "git.push" in commands
