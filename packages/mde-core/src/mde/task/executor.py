from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from mde.automation.fix_loop import execute_workflow_with_fix_loop
from mde.config.project import PROJECT_CONFIG_PATH, load_project_config
from mde.git.branches import validate_task_branch
from mde.git.repository import current_branch
from mde.plugins.runtime import create_runtime_registry
from mde.task.checkpoint import CheckpointStore, TaskCheckpoint, utc_iso
from mde.task.concurrency import TaskExecutionLock
from mde.task.store import TaskStore
from mde.task.types import TaskDefinition, TaskResult, utc_now
from mde.workflow.executor import WorkflowExecutionError
from mde.workflow.loader import load_named_workflow
from mde.workflow.models import WorkflowContext, WorkflowDefinition
from mde.workflow.registry import CommandRegistry


def apply_execution_policy(
    workflow: WorkflowDefinition, task: TaskDefinition
) -> WorkflowDefinition:
    """Disable policy-controlled steps without changing the YAML definition."""
    disabled_commands: set[str] = set()
    if not task.execution.auto_apply:
        disabled_commands.add("change.apply")
    if not task.execution.run_tests:
        disabled_commands.add("test.run")
    disabled_commands.update({"git.save", "git.push"})
    steps = tuple(
        replace(step, enabled=False) if step.command in disabled_commands else step
        for step in workflow.steps
    )
    return replace(workflow, steps=steps)


def execute_task(
    task: TaskDefinition,
    repository_root: Path,
    *,
    store: TaskStore | None = None,
    registry: CommandRegistry | None = None,
    resume: bool = True,
) -> TaskResult:
    root = repository_root.resolve()
    if (root / PROJECT_CONFIG_PATH).is_file():
        validate_task_branch(
            task,
            load_project_config(root),
            active_branch=current_branch(root),
        )
    task_store = store or TaskStore(root)
    checkpoints = CheckpointStore(root)

    with TaskExecutionLock(root, task.task_id):
        active = task_store.claim(task)
        started = utc_now()
        workflow = apply_execution_policy(
            load_named_workflow(active.workflow, root), active
        )
        prior = checkpoints.load(active.task_id) if resume else None
        completed_steps = prior.completed_steps if prior else ()

        def checkpoint_callback(step_id: str, successful: tuple[str, ...]) -> None:
            checkpoints.write(
                TaskCheckpoint(
                    task_id=active.task_id,
                    workflow=active.workflow,
                    status="processing",
                    completed_steps=successful,
                    last_successful_step=step_id,
                    updated_at=utc_iso(),
                )
            )

        context = WorkflowContext(
            workflow_name=workflow.name,
            message=active.title,
            repository_root=root,
            task_id=active.task_id,
            data={
                "task": active,
                "description": active.description,
                "inputs": active.inputs,
                "execution": active.execution,
                "completed_steps": completed_steps,
                "checkpoint_callback": checkpoint_callback,
            },
        )

        try:
            ai_inputs = active.inputs.get("ai", {})
            max_fix_attempts = (
                int(ai_inputs.get("max_fix_attempts", 0))
                if isinstance(ai_inputs, dict)
                else 0
            )
            workflow_result = execute_workflow_with_fix_loop(
                workflow,
                context,
                registry or create_runtime_registry(),
                max_fix_attempts=max_fix_attempts,
            )
            steps = tuple(
                {
                    "id": step.step_id,
                    "command": step.command,
                    "status": step.status,
                    "attempts": step.attempts,
                    "error": step.error,
                }
                for step in workflow_result.steps
            )
            last_successful = next(
                (
                    step["id"]
                    for step in reversed(steps)
                    if step["status"] in {"completed", "skipped"}
                ),
                None,
            )
            completed = TaskResult(
                task_id=active.task_id,
                status="completed",
                workflow=active.workflow,
                started_at=started,
                completed_at=utc_now(),
                steps=steps,
                summary=f"Task completed: {active.title}",
                last_successful_step=last_successful,
            )
            result_path = task_store.complete(active, completed)
            checkpoints.write(
                TaskCheckpoint(
                    task_id=active.task_id,
                    workflow=active.workflow,
                    status="completed",
                    completed_steps=tuple(
                        step["id"]
                        for step in steps
                        if step["status"] in {"completed", "skipped"}
                    ),
                    last_successful_step=last_successful,
                    updated_at=utc_iso(),
                )
            )
            return TaskResult(**{**completed.__dict__, "result_path": result_path})
        except Exception as error:
            workflow_steps = ()
            last_successful = prior.last_successful_step if prior else None
            if isinstance(error, WorkflowExecutionError):
                workflow_steps = tuple(
                    {
                        "id": step.step_id,
                        "command": step.command,
                        "status": step.status,
                        "attempts": step.attempts,
                        "error": step.error,
                    }
                    for step in error.result.steps
                )
                last_successful = next(
                    (
                        step["id"]
                        for step in reversed(workflow_steps)
                        if step["status"] in {"completed", "skipped"}
                    ),
                    last_successful,
                )
            failed = TaskResult(
                task_id=active.task_id,
                status="failed",
                workflow=active.workflow,
                started_at=started,
                completed_at=utc_now(),
                steps=workflow_steps,
                summary=f"Task failed: {active.title}",
                error=str(error),
                last_successful_step=last_successful,
            )
            result_path = task_store.fail(active, failed)
            current = checkpoints.load(active.task_id)
            checkpoints.write(
                TaskCheckpoint(
                    task_id=active.task_id,
                    workflow=active.workflow,
                    status="failed",
                    completed_steps=(
                        current.completed_steps if current else completed_steps
                    ),
                    last_successful_step=last_successful,
                    updated_at=utc_iso(),
                    error=str(error),
                )
            )
            return TaskResult(**{**failed.__dict__, "result_path": result_path})
