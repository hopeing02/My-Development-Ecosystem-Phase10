from dataclasses import replace
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


@pytest.mark.parametrize("failure", [None, "git.save", "git.push", "release.deploy"])
def test_repaired_workflow_runs_remaining_steps_and_propagates_failure(
    tmp_path: Path, failure: str | None
) -> None:
    calls: list[str] = []
    checkpoints: list[tuple[str, tuple[str, ...]]] = []
    registry = CommandRegistry()

    def handler(context, step):
        calls.append(step.command)
        if step.command == "test.run" and calls.count("test.run") == 1:
            raise RuntimeError("initial test failure")
        if step.command == failure:
            raise RuntimeError(f"{failure} failed")
        if step.command == "git.save":
            assert context.outputs["test"]["passed"] == 1
        return {"passed": 1}

    commands = ("git.save", "git.push", "release.deploy", "task.complete")
    for command in ("ai.generate", "ai.fix", "change.apply", "test.run", *commands):
        registry.register(command, handler)
    tail = (
        WorkflowStep(id="save", command="git.save", depends_on=("test",)),
        WorkflowStep(id="push", command="git.push", depends_on=("save",)),
        WorkflowStep(id="deploy", command="release.deploy", depends_on=("push",)),
        WorkflowStep(id="complete", command="task.complete", depends_on=("deploy",)),
    )
    definition = replace(workflow(), steps=workflow().steps + tail)
    context = WorkflowContext(
        "feature",
        repository_root=tmp_path,
        data={
            "completed_steps": (),
            "checkpoint_callback": lambda step_id, completed: checkpoints.append(
                (step_id, completed)
            ),
        },
    )
    if failure is None:
        result = execute_workflow_with_fix_loop(
            definition, context, registry, max_fix_attempts=2
        )
        assert result.status == "completed"
        assert [s.step_id for s in result.steps[-4:]] == [
            "save",
            "push",
            "deploy",
            "complete",
        ]
    else:
        with pytest.raises(WorkflowExecutionError) as caught:
            execute_workflow_with_fix_loop(
                definition, context, registry, max_fix_attempts=2
            )
        result = caught.value.result
        assert result.status == "failed"
        assert result.steps[-1].command == failure
        assert "exhausted" not in str(caught.value)
    expected_tail = (
        commands if failure is None else commands[: commands.index(failure) + 1]
    )
    assert calls == [
        "ai.generate",
        "change.apply",
        "test.run",
        "ai.fix",
        "change.apply",
        "test.run",
        *expected_tail,
    ]
    assert context.data["completed_steps"] == ()
    assert any(
        step_id == "test" and {"generate", "apply", "test"} <= set(done)
        for step_id, done in checkpoints
    )
    assert all(not step_id.startswith("auto-") for step_id, _ in checkpoints)


def test_failed_repairs_preserve_checkpoint_and_never_publish(tmp_path: Path) -> None:
    calls: list[str] = []
    checkpoints: list[tuple[str, tuple[str, ...]]] = []
    registry = CommandRegistry()

    def handler(context, step):
        calls.append(step.command)
        if step.command == "test.run":
            raise RuntimeError("still failing")
        return {}

    for command in ("ai.generate", "ai.fix", "change.apply", "test.run", "git.save"):
        registry.register(command, handler)
    definition = replace(
        workflow(),
        steps=workflow().steps
        + (WorkflowStep(id="save", command="git.save", depends_on=("test",)),),
    )
    context = WorkflowContext(
        "feature",
        repository_root=tmp_path,
        data={
            "checkpoint_callback": lambda step_id, done: checkpoints.append(
                (step_id, done)
            )
        },
    )
    with pytest.raises(WorkflowExecutionError):
        execute_workflow_with_fix_loop(
            definition, context, registry, max_fix_attempts=2
        )
    assert "git.save" not in calls
    assert checkpoints[-1] == ("apply", ("apply", "generate"))


def test_repaired_workflow_respects_disabled_and_conditional_steps(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    registry = CommandRegistry()

    def handler(context, step):
        calls.append(step.command)
        if step.command == "test.run" and calls.count("test.run") == 1:
            raise RuntimeError("initial test failure")
        return {}

    for command in (
        "ai.generate",
        "ai.fix",
        "change.apply",
        "test.run",
        "task.complete",
    ):
        registry.register(command, handler)
    definition = replace(
        workflow(),
        steps=workflow().steps
        + (
            WorkflowStep(
                id="save", command="git.save", enabled=False, depends_on=("test",)
            ),
            WorkflowStep(
                id="push", command="git.push", condition="false", depends_on=("save",)
            ),
            WorkflowStep(id="complete", command="task.complete", depends_on=("push",)),
        ),
    )
    result = execute_workflow_with_fix_loop(
        definition,
        WorkflowContext("feature", repository_root=tmp_path),
        registry,
        max_fix_attempts=1,
    )
    assert result.status == "completed"
    assert [step.status for step in result.steps[-3:]] == [
        "skipped",
        "skipped",
        "completed",
    ]
    assert "git.save" not in calls and "git.push" not in calls


def test_fix_loop_retests_the_actual_failed_test_step(tmp_path: Path) -> None:
    seen: list[tuple[str, dict]] = []
    registry = CommandRegistry()

    def handler(context, step):
        seen.append((step.id, step.args))
        if step.id == "second-test":
            raise RuntimeError("second test failed")
        if step.id.startswith("auto-retest"):
            assert step.args == {"suite": "second"}
        return {"passed": 1}

    for command in ("ai.generate", "ai.fix", "change.apply", "test.run"):
        registry.register(command, handler)
    definition = replace(
        workflow(),
        steps=workflow().steps
        + (
            WorkflowStep(
                id="second-test",
                command="test.run",
                args={"suite": "second"},
                depends_on=("test",),
            ),
        ),
    )
    context = WorkflowContext("feature", repository_root=tmp_path)
    result = execute_workflow_with_fix_loop(
        definition, context, registry, max_fix_attempts=1
    )
    assert result.status == "completed"
    assert context.outputs["second-test"] == {"passed": 1}
    assert len([step_id for step_id, _ in seen if step_id == "test"]) == 1
