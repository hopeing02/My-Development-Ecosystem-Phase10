import pytest

from mde.workflow.registry import CommandNotRegisteredError, CommandRegistry


def test_registers_and_resolves_handler() -> None:
    registry = CommandRegistry()
    handler = lambda context, step: None
    registry.register("sample.run", handler)
    assert registry.get("sample.run") is handler


def test_rejects_duplicate_registration() -> None:
    registry = CommandRegistry()
    registry.register("sample.run", lambda context, step: None)
    with pytest.raises(ValueError):
        registry.register("sample.run", lambda context, step: None)


def test_unknown_command_has_clear_error() -> None:
    with pytest.raises(CommandNotRegisteredError, match="not registered"):
        CommandRegistry().get("missing")
