from __future__ import annotations

from typing import Any

from mde.git import repository as git
from mde.workflow.models import WorkflowContext, WorkflowStep
from mde.workflow.registry import CommandRegistry


def save_changes(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
    changes = git.changed_files(context.repository_root)
    if not changes:
        return {
            "message": "No changes to commit.",
            "commit_hash": None,
            "changed_files": [],
        }
    message = str(
        step.args.get("message")
        or context.data.get("commit_message")
        or context.message
        or f"mde: complete {context.task_id or context.workflow_name}"
    )
    git.add(repository_root=context.repository_root)
    commit_hash = git.commit(message, repository_root=context.repository_root)
    context.data["commit_hash"] = commit_hash
    return {
        "message": "Changes committed.",
        "commit_hash": commit_hash,
        "changed_files": list(changes),
    }


def push_changes(context: WorkflowContext, step: WorkflowStep) -> dict[str, Any]:
    remote = str(step.args.get("remote", context.data.get("git_remote", "origin")))
    branch_value = step.args.get("branch", context.data.get("git_branch"))
    branch = str(branch_value) if branch_value else None
    git.push(remote=remote, branch=branch, repository_root=context.repository_root)
    return {"message": "Changes pushed.", "remote": remote, "branch": branch}


class GitWorkflowPlugin:
    name = "git"

    def register(self, registry: CommandRegistry) -> None:
        registry.register("git.save", save_changes)
        registry.register("git.push", push_changes)
