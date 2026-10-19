from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mde.exceptions import MDEError
from mde.workflow.models import WorkflowContext, WorkflowStep

CommandHandler = Callable[[WorkflowContext, WorkflowStep], dict[str, Any] | None]


class CommandNotRegisteredError(MDEError, LookupError):
    """Raised when a workflow references an unknown command ID."""


class CommandRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, CommandHandler] = {}

    def register(
        self, command_id: str, handler: CommandHandler, *, replace: bool = False
    ) -> None:
        if not command_id.strip():
            raise ValueError("command_id must not be empty.")
        if command_id in self._handlers and not replace:
            raise ValueError(f"Command '{command_id}' is already registered.")
        self._handlers[command_id] = handler

    def get(self, command_id: str) -> CommandHandler:
        try:
            return self._handlers[command_id]
        except KeyError as error:
            available = ", ".join(self.list_commands()) or "none"
            raise CommandNotRegisteredError(
                f"Command '{command_id}' is not registered. Available: {available}"
            ) from error

    def list_commands(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))


def _record_step(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
    message = str(step.args.get("message", step.id))
    context.outputs[step.id] = {
        "command": step.command,
        "message": message,
    }
    return {"message": message}


def create_default_registry() -> CommandRegistry:
    registry = CommandRegistry()
    for command_id in (
        "task.prepare",
        "ai.generate",
        "change.review",
        "change.apply",
        "test.run",
        "git.save",
        "git.push",
        "task.complete",
        "docs.generate",
        "refactor.plan",
        "bugfix.analyze",
    ):
        registry.register(command_id, _record_step)
    return registry
