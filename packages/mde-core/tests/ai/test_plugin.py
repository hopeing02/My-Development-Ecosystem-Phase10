from pathlib import Path
from dataclasses import replace

import pytest

from mde.plugins.builtin.ai import AIWorkflowPlugin
from mde.ai.engine import AIEngine
from mde.ai.providers.mock import MockAIProvider
from mde.ai.registry import AIProviderRegistry
from mde.workflow.executor import execute_workflow, WorkflowExecutionError
from mde.workflow.models import WorkflowDefinition
from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


def test_fix_receives_current_source_and_actual_failed_test_log(tmp_path, monkeypatch):
    import sys
    from mde.plugins.builtin.testing import run_tests, TestExecutionError

    (tmp_path / "service.py").write_text("broken source", encoding="utf-8")
    context = WorkflowContext(
        "context",
        repository_root=tmp_path,
        data={
            "inputs": {"ai": {"context_files": ["service.py"]}},
            "testing_command": [
                sys.executable,
                "-c",
                "import sys;print('actual assertion failure');sys.exit(1)",
            ],
        },
    )
    with pytest.raises(TestExecutionError):
        run_tests(context, WorkflowStep("test", "test.run"))
    provider = MockAIProvider()
    original = provider.execute

    def response(request):
        assert request.context["files"] == [
            {"path": "service.py", "content": "broken source"}
        ]
        assert "actual assertion failure" in request.context["test_failure_log"]
        return original(request)

    monkeypatch.setattr(provider, "execute", response)
    providers = AIProviderRegistry()
    providers.register(provider)
    AIWorkflowPlugin(AIEngine(providers)).fix(context, WorkflowStep("fix", "ai.fix"))


@pytest.mark.parametrize("paths", [["../outside"], ["missing"], ["x"] * 21, "not-list"])
def test_context_files_reject_invalid_inputs(tmp_path, paths):
    context = WorkflowContext(
        "context",
        repository_root=tmp_path,
        data={"inputs": {"ai": {"context_files": paths}}},
    )
    from mde.ai.artifacts import ArtifactError

    with pytest.raises(ArtifactError):
        AIWorkflowPlugin().generate(context, WorkflowStep("generate", "ai.generate"))


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


@pytest.mark.parametrize("verdict", [None, False, "true", True])
def test_review_requires_explicit_approval_and_receives_generated_content(
    tmp_path: Path, monkeypatch, verdict
) -> None:
    target = tmp_path / "output.txt"
    target.write_text("original", encoding="utf-8")
    provider = MockAIProvider()
    original = provider.execute

    def response(request):
        if request.action == "generate":
            request = replace(
                request,
                context={
                    "artifacts": [
                        {"path": "output.txt", "content": "actual generated code"}
                    ]
                },
            )
        if request.action == "review":
            assert request.context["artifacts"] == [
                {"path": "output.txt", "content": "actual generated code"}
            ]
            return replace(original(request), metadata={"approved": verdict})
        return original(request)

    monkeypatch.setattr(provider, "execute", response)
    providers = AIProviderRegistry()
    providers.register(provider)
    registry = CommandRegistry()
    AIWorkflowPlugin(AIEngine(providers)).register(registry)
    definition = WorkflowDefinition(
        1,
        "review",
        "review gate",
        (
            WorkflowStep("generate", "ai.generate"),
            WorkflowStep("review", "change.review", depends_on=("generate",)),
            WorkflowStep("apply", "change.apply", depends_on=("review",)),
        ),
    )
    context = WorkflowContext(
        "review",
        repository_root=tmp_path,
        data={"inputs": {"ai": {"provider": "mock"}}},
    )
    if verdict is True:
        assert execute_workflow(definition, context, registry).status == "completed"
        assert target.read_text() == "actual generated code"
    else:
        with pytest.raises(WorkflowExecutionError) as caught:
            execute_workflow(definition, context, registry)
        assert caught.value.result.steps[-1].command == "change.review"
        assert target.read_text() == "original"
