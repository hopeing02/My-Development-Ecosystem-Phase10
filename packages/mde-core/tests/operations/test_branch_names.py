from dataclasses import replace

import pytest

from mde.config.project import validate_project_document
from mde.git.branches import (
    BranchPolicyError,
    branch_name_for_task,
    expected_branch_for_task,
    validate_task_branch,
)
from mde.task.loader import validate_task_document


def test_branch_name_for_task_is_safe() -> None:
    assert branch_name_for_task("TASK 001", "Feature") == "feature/task-001"


def collaboration_config():
    return validate_project_document(
        {
            "version": 1,
            "project": {"id": "sample", "name": "Sample"},
            "repository": {
                "default_branch": "main",
                "branch_pattern": "{type}/{assignee}/{task_id}",
            },
            "commands": {"test": [], "build": []},
        }
    )


def assigned_task():
    return validate_task_document(
        {
            "version": 1,
            "task": {
                "id": "TASK-001",
                "type": "Feature",
                "title": "Collaborate",
                "workflow": "feature",
                "assignee": "GitHub-User",
                "repository": {"base_branch": "main"},
            },
        }
    )


def test_branch_name_includes_assignee() -> None:
    task = assigned_task()

    assert expected_branch_for_task(task, collaboration_config()) == (
        "feature/github-user/task-001"
    )


def test_rejects_task_without_assignee_for_collaboration() -> None:
    task = replace(assigned_task(), assignee=None)

    with pytest.raises(BranchPolicyError, match="assignee"):
        expected_branch_for_task(task, collaboration_config())


def test_rejects_configured_or_active_branch_mismatch() -> None:
    task = replace(assigned_task(), branch="feature/other/task-001")

    with pytest.raises(BranchPolicyError, match="Task branch mismatch"):
        validate_task_branch(task, collaboration_config())

    task = replace(task, branch=None)
    with pytest.raises(BranchPolicyError, match="Active branch mismatch"):
        validate_task_branch(task, collaboration_config(), active_branch="main")
