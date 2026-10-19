from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from mde.workflow.executor import WorkflowExecutionError, execute_workflow
from mde.workflow.models import (
    WorkflowContext,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStep,
)
from mde.workflow.registry import CommandRegistry


def _find_step(workflow: WorkflowDefinition, command: str) -> WorkflowStep | None:
    return next((step for step in workflow.steps if step.command == command), None)


def _single_step_workflow(
    name: str, steps: Iterable[WorkflowStep]
) -> WorkflowDefinition:
    normalized = tuple(replace(step, depends_on=()) for step in steps)
    return WorkflowDefinition(version=1, name=name, description=name, steps=normalized)


def execute_workflow_with_fix_loop(
    workflow: WorkflowDefinition,
    context: WorkflowContext,
    registry: CommandRegistry,
    *,
    max_fix_attempts: int = 0,
) -> WorkflowResult:
    """Execute a workflow and repair test failures with ai.fix/apply/retest.

    The normal workflow runs once. Only failures at ``test.run`` are eligible for
    repair. Each repair cycle executes ``ai.fix`` then ``change.apply`` and finally
    ``test.run``. The loop is bounded by ``max_fix_attempts``.
    """
    try:
        return execute_workflow(workflow, context, registry)
    except WorkflowExecutionError as initial_error:
        failed_step = (
            initial_error.result.steps[-1] if initial_error.result.steps else None
        )
        if (
            max_fix_attempts <= 0
            or failed_step is None
            or failed_step.command != "test.run"
        ):
            raise

        fix_step = _find_step(workflow, "ai.fix") or WorkflowStep(
            id="auto-fix", command="ai.fix"
        )
        apply_step = _find_step(workflow, "change.apply") or WorkflowStep(
            id="auto-apply-fix", command="change.apply"
        )
        test_step = _find_step(workflow, "test.run")
        if test_step is None:
            raise

        context.data["last_test_error"] = failed_step.error
        context.data["fix_attempt"] = 0
        accumulated = list(initial_error.result.steps)
        last_error = initial_error

        for attempt in range(1, max_fix_attempts + 1):
            context.data["fix_attempt"] = attempt
            repair = _single_step_workflow(
                f"{workflow.name}-fix-{attempt}",
                (
                    replace(fix_step, id=f"auto-fix-{attempt}"),
                    replace(apply_step, id=f"auto-apply-fix-{attempt}"),
                    replace(test_step, id=f"auto-retest-{attempt}"),
                ),
            )
            try:
                repaired = execute_workflow(repair, context, registry)
                accumulated.extend(repaired.steps)
                return WorkflowResult(
                    workflow_name=workflow.name,
                    status="completed",
                    started_at=initial_error.result.started_at,
                    completed_at=repaired.completed_at,
                    steps=tuple(accumulated),
                )
            except WorkflowExecutionError as repair_error:
                accumulated.extend(repair_error.result.steps)
                last_error = repair_error
                failed = (
                    repair_error.result.steps[-1] if repair_error.result.steps else None
                )
                context.data["last_test_error"] = (
                    failed.error if failed else str(repair_error)
                )
                if failed is None or failed.command != "test.run":
                    break

        final = WorkflowResult(
            workflow_name=workflow.name,
            status="failed",
            started_at=initial_error.result.started_at,
            completed_at=last_error.result.completed_at,
            steps=tuple(accumulated),
            error=f"Automatic fix loop exhausted after {max_fix_attempts} attempt(s): {last_error}",
        )
        raise WorkflowExecutionError(
            final.error or "Automatic fix loop failed", final
        ) from last_error
