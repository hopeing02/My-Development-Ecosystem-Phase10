from pathlib import Path

from mde.plugins.builtin.ai import AIWorkflowPlugin
from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


def test_ai_plugin_generate_and_apply(tmp_path: Path) -> None:
    registry = CommandRegistry()
    AIWorkflowPlugin().register(registry)
    context = WorkflowContext(
        workflow_name="feature",
        repository_root=tmp_path,
        task_id="TASK-1",
        message="create file",
        data={
            "inputs": {
                "ai": {
                    "provider": "mock",
                    "artifacts": [{"path": "src/output.txt", "content": "generated"}],
                }
            }
        },
    )
    generate = WorkflowStep(id="generate", command="ai.generate")
    generated = registry.get("ai.generate")(context, generate)
    context.outputs["generate"] = generated

    apply = WorkflowStep(id="apply", command="change.apply")
    applied = registry.get("change.apply")(context, apply)

    assert (tmp_path / "src/output.txt").read_text() == "generated"
    assert applied["changed_files"] == ["src/output.txt"]


def test_apply_creates_backup_for_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "src/output.txt"
    target.parent.mkdir(parents=True)
    target.write_text("old")
    registry = CommandRegistry()
    AIWorkflowPlugin().register(registry)
    context = WorkflowContext(
        workflow_name="feature",
        repository_root=tmp_path,
        task_id="TASK-2",
        data={"inputs": {"artifacts": [{"path": "src/output.txt", "content": "new"}]}},
    )
    generated = registry.get("ai.generate")(
        context, WorkflowStep(id="generate", command="ai.generate")
    )
    context.outputs["generate"] = generated
    registry.get("change.apply")(
        context, WorkflowStep(id="apply", command="change.apply")
    )

    assert target.read_text() == "new"
    assert (tmp_path / ".mde/backups/TASK-2/apply/src/output.txt").read_text() == "old"
