from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mde.exceptions import MDEError
from mde.workflow.models import WorkflowDefinition, WorkflowStep


class WorkflowValidationError(MDEError, ValueError):
    """Raised when a workflow document is structurally invalid."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowValidationError(f"'{field_name}' must be a non-empty string.")
    return value.strip()


def _parse_step(raw: Any, index: int) -> WorkflowStep:
    if not isinstance(raw, Mapping):
        raise WorkflowValidationError(f"Step {index} must be a mapping.")

    step_id = _require_text(raw.get("id"), f"steps[{index}].id")
    command = _require_text(raw.get("command"), f"steps[{index}].command")

    args = raw.get("args", {})
    if args is None:
        args = {}
    if not isinstance(args, Mapping):
        raise WorkflowValidationError(f"steps[{index}].args must be a mapping.")

    depends_on = raw.get("depends_on", [])
    if depends_on is None:
        depends_on = []
    if not isinstance(depends_on, list) or not all(
        isinstance(item, str) for item in depends_on
    ):
        raise WorkflowValidationError(
            f"steps[{index}].depends_on must be a list of strings."
        )

    timeout = raw.get("timeout")
    if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
        raise WorkflowValidationError(
            f"steps[{index}].timeout must be a positive integer."
        )

    retry = raw.get("retry", 0)
    if not isinstance(retry, int) or retry < 0:
        raise WorkflowValidationError(
            f"steps[{index}].retry must be a non-negative integer."
        )

    for bool_field in ("enabled", "continue_on_error"):
        value = raw.get(bool_field, True if bool_field == "enabled" else False)
        if not isinstance(value, bool):
            raise WorkflowValidationError(
                f"steps[{index}].{bool_field} must be boolean."
            )

    condition = raw.get("condition")
    if condition is not None and not isinstance(condition, str):
        raise WorkflowValidationError(f"steps[{index}].condition must be a string.")

    return WorkflowStep(
        id=step_id,
        command=command,
        args=dict(args),
        depends_on=tuple(depends_on),
        enabled=raw.get("enabled", True),
        continue_on_error=raw.get("continue_on_error", False),
        timeout=timeout,
        retry=retry,
        condition=condition,
    )


def validate_workflow_document(document: Any) -> WorkflowDefinition:
    if not isinstance(document, Mapping):
        raise WorkflowValidationError("Workflow document must be a mapping.")

    version = document.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise WorkflowValidationError("'version' must be a positive integer.")

    name = _require_text(document.get("name"), "name")
    description = document.get("description", "")
    if not isinstance(description, str):
        raise WorkflowValidationError("'description' must be a string.")

    raw_steps = document.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise WorkflowValidationError("'steps' must be a non-empty list.")

    steps = tuple(_parse_step(raw, index) for index, raw in enumerate(raw_steps))
    ids = [step.id for step in steps]
    if len(ids) != len(set(ids)):
        raise WorkflowValidationError("Workflow step IDs must be unique.")

    known_ids = set(ids)
    for step in steps:
        unknown = set(step.depends_on) - known_ids
        if unknown:
            raise WorkflowValidationError(
                f"Step '{step.id}' depends on unknown steps: {', '.join(sorted(unknown))}."
            )
        if step.id in step.depends_on:
            raise WorkflowValidationError(f"Step '{step.id}' cannot depend on itself.")

    completed: set[str] = set()
    for step in steps:
        unresolved = set(step.depends_on) - completed
        if unresolved:
            raise WorkflowValidationError(
                f"Step '{step.id}' depends on steps that appear later: {', '.join(sorted(unresolved))}."
            )
        completed.add(step.id)

    return WorkflowDefinition(
        version=version,
        name=name,
        description=description.strip(),
        steps=steps,
    )
