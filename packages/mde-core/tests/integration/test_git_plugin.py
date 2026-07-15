import subprocess
from pathlib import Path

from mde.plugins.builtin.git import push_changes, save_changes
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
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
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
