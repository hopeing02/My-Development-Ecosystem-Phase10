from __future__ import annotations

from datetime import datetime
from typing import Any

from mde.workflow.models import (
    StepResult,
    WorkflowContext,
    WorkflowDefinition,
    WorkflowResult,
    utc_now,
)
from mde.workflow.registry import CommandRegistry


class WorkflowExecutionError(RuntimeError):
    def __init__(self, message: str, result: WorkflowResult) -> None:
        super().__init__(message)
        self.result = result


def _condition_is_true(condition: str | None, context: WorkflowContext) -> bool:
    if condition is None or not condition.strip():
        return True
    normalized = condition.strip().lower()
    if normalized in {"true", "always"}:
        return True
    if normalized in {"false", "never"}:
        return False
    if normalized.startswith("data."):
        return bool(context.data.get(condition[5:]))
    raise ValueError(f"Unsupported workflow condition: {condition}")


def execute_workflow(
    workflow: WorkflowDefinition,
    context: WorkflowContext,
    registry: CommandRegistry,
) -> WorkflowResult:
    workflow_started = utc_now()
    results: list[StepResult] = []
    successful_steps: set[str] = set()
    resumed_steps = set(context.data.get("completed_steps", ()))
    checkpoint_callback = context.data.get("checkpoint_callback")

    for step in workflow.steps:
        if step.id in resumed_steps:
            now = utc_now()
            results.append(
                StepResult(
                    step_id=step.id,
                    command=step.command,
                    status="skipped",
                    started_at=now,
                    completed_at=now,
                    message="Step restored from checkpoint.",
                    attempts=0,
                )
            )
            successful_steps.add(step.id)
            continue
        if not step.enabled or not _condition_is_true(step.condition, context):
            now = utc_now()
            results.append(
                StepResult(
                    step_id=step.id,
                    command=step.command,
                    status="skipped",
                    started_at=now,
                    completed_at=now,
                    message="Step disabled or condition evaluated to false.",
                    attempts=0,
                )
            )
            successful_steps.add(step.id)
            continue

        missing = set(step.depends_on) - successful_steps
        if missing:
            error_message = f"Dependencies not completed for step '{step.id}': {', '.join(sorted(missing))}"
            now = utc_now()
            results.append(
                StepResult(
                    step_id=step.id,
                    command=step.command,
                    status="failed",
                    started_at=now,
                    completed_at=now,
                    error=error_message,
                    attempts=0,
                )
            )
            final = WorkflowResult(
                workflow_name=workflow.name,
                status="failed",
                started_at=workflow_started,
                completed_at=now,
                steps=tuple(results),
                error=error_message,
            )
            raise WorkflowExecutionError(error_message, final)

        handler = registry.get(step.command)
        step_started: datetime = utc_now()
        last_error: Exception | None = None
        outputs: dict[str, Any] = {}
        attempts = step.retry + 1

        for attempt in range(1, attempts + 1):
            try:
                returned = handler(context, step)
                outputs = dict(returned or {})
                completed = utc_now()
                results.append(
                    StepResult(
                        step_id=step.id,
                        command=step.command,
                        status="completed",
                        started_at=step_started,
                        completed_at=completed,
                        outputs=outputs,
                        message=str(outputs.get("message", "")),
                        attempts=attempt,
                    )
                )
                context.outputs[step.id] = outputs
                successful_steps.add(step.id)
                if callable(checkpoint_callback):
                    checkpoint_callback(step.id, tuple(sorted(successful_steps)))
                last_error = None
                break
            except Exception as error:  # command boundary
                last_error = error

        if last_error is not None:
            completed = utc_now()
            error_message = str(last_error)
            results.append(
                StepResult(
                    step_id=step.id,
                    command=step.command,
                    status="failed",
                    started_at=step_started,
                    completed_at=completed,
                    error=error_message,
                    attempts=attempts,
                )
            )
            if step.continue_on_error:
                successful_steps.add(step.id)
                continue

            final = WorkflowResult(
                workflow_name=workflow.name,
                status="failed",
                started_at=workflow_started,
                completed_at=completed,
                steps=tuple(results),
                error=error_message,
            )
            raise WorkflowExecutionError(
                f"Workflow '{workflow.name}' failed at step '{step.id}': {error_message}",
                final,
            ) from last_error

    return WorkflowResult(
        workflow_name=workflow.name,
        status="completed",
        started_at=workflow_started,
        completed_at=utc_now(),
        steps=tuple(results),
    )
