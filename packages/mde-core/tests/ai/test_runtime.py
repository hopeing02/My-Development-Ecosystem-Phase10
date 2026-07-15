from mde.plugins.runtime import create_runtime_plugin_manager, create_runtime_registry


def test_runtime_includes_ai_plugin() -> None:
    assert create_runtime_plugin_manager().names() == ("core", "ai", "testing", "git")


def test_runtime_registers_ai_commands() -> None:
    commands = create_runtime_registry().list_commands()
    assert "ai.generate" in commands
    assert "change.apply" in commands
    assert "ai.fix" in commands
