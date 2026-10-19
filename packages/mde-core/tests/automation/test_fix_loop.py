from pathlib import Path

import pytest

from mde.automation.fix_loop import execute_workflow_with_fix_loop
from mde.workflow.executor import WorkflowExecutionError
from mde.workflow.models import WorkflowContext, WorkflowDefinition, WorkflowStep
from mde.workflow.registry import CommandRegistry


def workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        version=1,
        name="feature",
        description="test",
        steps=(
            WorkflowStep(id="generate", command="ai.generate"),
            WorkflowStep(id="apply", command="change.apply", depends_on=("generate",)),
            WorkflowStep(id="test", command="test.run", depends_on=("apply",)),
        ),
    )


def test_fix_loop_repairs_a_test_failure(tmp_path: Path) -> None:
    calls: list[str] = []
    test_runs = {"count": 0}
    registry = CommandRegistry()
    registry.register("ai.generate", lambda c, s: calls.append(s.command) or {})
    registry.register(
        "ai.fix", lambda c, s: calls.append(s.command) or {"manifest_path": "fix"}
    )
    registry.register("change.apply", lambda c, s: calls.append(s.command) or {})

    def test_handler(context, step):
        calls.append(step.command)
        test_runs["count"] += 1
        if test_runs["count"] == 1:
            raise RuntimeError("one failing test")
        return {"passed": 1}

    registry.register("test.run", test_handler)
    result = execute_workflow_with_fix_loop(
        workflow(),
        WorkflowContext("feature", repository_root=tmp_path),
        registry,
        max_fix_attempts=2,
    )
    assert result.status == "completed"
    assert calls == [
        "ai.generate",
        "change.apply",
        "test.run",
        "ai.fix",
        "change.apply",
        "test.run",
    ]


def test_fix_loop_stops_after_limit(tmp_path: Path) -> None:
    registry = CommandRegistry()
    registry.register("ai.generate", lambda c, s: {})
    registry.register("ai.fix", lambda c, s: {})
    registry.register("change.apply", lambda c, s: {})
    registry.register(
        "test.run", lambda c, s: (_ for _ in ()).throw(RuntimeError("still failing"))
    )

    with pytest.raises(WorkflowExecutionError) as caught:
        execute_workflow_with_fix_loop(
            workflow(),
            WorkflowContext("feature", repository_root=tmp_path),
            registry,
            max_fix_attempts=2,
        )
    assert "exhausted after 2" in str(caught.value)
    assert len([s for s in caught.value.result.steps if s.command == "ai.fix"]) == 2
