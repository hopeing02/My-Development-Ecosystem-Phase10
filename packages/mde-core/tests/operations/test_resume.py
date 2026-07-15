from pathlib import Path

from mde.workflow.executor import execute_workflow
from mde.workflow.models import WorkflowContext, WorkflowDefinition, WorkflowStep
from mde.workflow.registry import CommandRegistry


def test_workflow_restores_completed_steps_from_checkpoint(tmp_path: Path) -> None:
    calls: list[str] = []
    registry = CommandRegistry()
    registry.register("one", lambda context, step: calls.append("one") or {})
    registry.register("two", lambda context, step: calls.append("two") or {})
    workflow = WorkflowDefinition(
        version=1,
        name="resume",
        description="",
        steps=(
            WorkflowStep(id="first", command="one"),
            WorkflowStep(id="second", command="two", depends_on=("first",)),
        ),
    )
    context = WorkflowContext(
        workflow_name="resume",
        message="",
        repository_root=tmp_path,
        data={"completed_steps": ("first",)},
    )
    result = execute_workflow(workflow, context, registry)
    assert calls == ["two"]
    assert result.steps[0].status == "skipped"
    assert "checkpoint" in result.steps[0].message.lower()
