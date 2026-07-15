from pathlib import Path

import pytest

from mde.workflow.executor import WorkflowExecutionError, execute_workflow
from mde.workflow.models import WorkflowContext
from mde.workflow.registry import CommandRegistry
from mde.workflow.validator import validate_workflow_document


def make_workflow(retry: int = 0):
    return validate_workflow_document(
        {
            "version": 1,
            "name": "sample",
            "steps": [
                {"id": "first", "command": "sample.first", "retry": retry},
                {"id": "second", "command": "sample.second", "depends_on": ["first"]},
            ],
        }
    )


def test_executes_registered_handlers_in_order(tmp_path: Path) -> None:
    calls = []
    registry = CommandRegistry()
    registry.register("sample.first", lambda context, step: calls.append(step.id) or {"value": 1})
    registry.register("sample.second", lambda context, step: calls.append(step.id) or {"value": 2})
    context = WorkflowContext("sample", repository_root=tmp_path)

    result = execute_workflow(make_workflow(), context, registry)

    assert result.status == "completed"
    assert calls == ["first", "second"]
    assert context.outputs["second"] == {"value": 2}


def test_retries_failed_handler(tmp_path: Path) -> None:
    attempts = {"count": 0}
    registry = CommandRegistry()

    def flaky(context, step):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary")
        return {"ok": True}

    registry.register("sample.first", flaky)
    registry.register("sample.second", lambda context, step: {})
    result = execute_workflow(
        make_workflow(retry=1), WorkflowContext("sample", repository_root=tmp_path), registry
    )
    assert result.steps[0].attempts == 2


def test_stops_on_failure(tmp_path: Path) -> None:
    registry = CommandRegistry()
    registry.register("sample.first", lambda context, step: (_ for _ in ()).throw(RuntimeError("boom")))
    registry.register("sample.second", lambda context, step: {})

    with pytest.raises(WorkflowExecutionError) as captured:
        execute_workflow(make_workflow(), WorkflowContext("sample", repository_root=tmp_path), registry)

    assert captured.value.result.status == "failed"
    assert captured.value.result.steps[-1].step_id == "first"
