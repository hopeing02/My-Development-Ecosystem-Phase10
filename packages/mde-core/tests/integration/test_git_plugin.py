import subprocess
import sys
from dataclasses import replace
from pathlib import Path

from mde.ai.providers.mock import MockAIProvider
from mde.ai.registry import AIProviderRegistry
from mde.automation.fix_loop import execute_workflow_with_fix_loop
from mde.plugins.builtin.git import push_changes, save_changes
from mde.plugins.runtime import create_runtime_registry
from mde.workflow.loader import load_named_workflow
from mde.workflow.models import WorkflowContext, WorkflowStep


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def configure_repository(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "mde@example.test")
    git(root, "config", "user.name", "MDE Test")


def test_git_plugins_commit_and_push_to_bare_remote(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    work = tmp_path / "work"
    work.mkdir()
    configure_repository(work)
    git(work, "remote", "add", "origin", str(remote))
    (work / "README.md").write_text("phase 6\n", encoding="utf-8")

    context = WorkflowContext(
        workflow_name="integration",
        message="phase 6 integration",
        repository_root=work,
        data={"git_branch": "main"},
    )
    saved = save_changes(context, WorkflowStep(id="save", command="git.save"))
    assert saved["commit_hash"] == git(work, "rev-parse", "HEAD")

    pushed = push_changes(context, WorkflowStep(id="push", command="git.push"))
    assert pushed["remote"] == "origin"
    assert git(remote, "rev-parse", "refs/heads/main") == saved["commit_hash"]


def test_repaired_feature_runs_real_pytest_then_commits_and_pushes(
    tmp_path: Path, monkeypatch
) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote)], check=True, capture_output=True
    )
    work = tmp_path / "work"
    work.mkdir()
    configure_repository(work)
    git(work, "remote", "add", "origin", str(remote))
    (work / ".gitignore").write_text(
        ".mde/\nlogs/\n__pycache__/\n.pytest_cache/\n", encoding="utf-8"
    )
    (work / "test_answer.py").write_text(
        "from answer import answer\n\ndef test_answer():\n    assert answer() == 42\n",
        encoding="utf-8",
    )
    git(work, "add", ".")
    git(work, "commit", "-m", "seed acceptance test")
    before = git(work, "rev-parse", "HEAD")
    provider = MockAIProvider()
    execute = provider.execute
    actions: list[str] = []

    def scripted_response(request):
        actions.append(request.action)
        artifacts = (
            []
            if request.action == "review"
            else [
                {
                    "path": "answer.py",
                    "content": f"def answer():\n    return {42 if request.action == 'fix' else 0}\n",
                }
            ]
        )
        return execute(replace(request, context={"artifacts": artifacts}))

    monkeypatch.setattr(provider, "execute", scripted_response)
    providers = AIProviderRegistry()
    providers.register(provider)
    monkeypatch.setattr(
        "mde.ai.engine.create_default_provider_registry", lambda: providers
    )
    context = WorkflowContext(
        workflow_name="feature",
        repository_root=work,
        task_id="ACCEPTANCE-REPAIR",
        message="implement answer",
        data={
            "inputs": {"ai": {"provider": "mock"}},
            "git_branch": "main",
            "testing_command": [sys.executable, "-m", "pytest", "-q", "--noconftest"],
        },
    )
    result = execute_workflow_with_fix_loop(
        load_named_workflow("feature", work),
        context,
        create_runtime_registry(),
        max_fix_attempts=1,
    )
    assert result.status == "completed"
    assert actions == ["generate", "review", "fix"]
    assert context.outputs["test"]["return_code"] == 0
    assert context.outputs["test"]["passed"] == 1
    assert "1 failed" in (work / "logs/tests/ACCEPTANCE-REPAIR-test.log").read_text()
    assert "1 passed" in Path(context.outputs["test"]["log_path"]).read_text()
    assert git(work, "rev-parse", "HEAD") != before
    assert git(remote, "rev-parse", "refs/heads/main") == git(work, "rev-parse", "HEAD")
    assert git(work, "status", "--porcelain") == ""
    assert result.steps[-1].step_id == "complete"
