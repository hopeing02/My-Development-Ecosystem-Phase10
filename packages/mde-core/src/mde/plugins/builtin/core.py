from __future__ import annotations

from typing import Any

from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


class CoreWorkflowPlugin:
    name = "core"

    @staticmethod
    def _record(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
        message = str(step.args.get("message", context.message or step.id))
        return {"message": message, "command": step.command}

    def register(self, registry: CommandRegistry) -> None:
        for command_id in (
            "task.prepare",
            "task.complete",
            "refactor.plan",
            "bugfix.analyze",
        ):
            registry.register(command_id, self._record)
