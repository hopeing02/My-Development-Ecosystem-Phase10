from pathlib import Path

import pytest

from mde.config.project import (
    ProjectConfigError,
    load_project_config,
    validate_project_document,
)


def valid_document() -> dict[str, object]:
    return {
        "version": 1,
        "project": {"id": "sample-project", "name": "Sample Project"},
        "repository": {
            "default_branch": "main",
            "branch_pattern": "{type}/{assignee}/{task_id}",
            "protected_branches": ["main"],
        },
        "commands": {
            "test": ["python -m pytest"],
            "build": ["python -m build"],
        },
        "pull_request": {
            "required": True,
            "approvals_required": 1,
            "require_tests": True,
        },
    }


def test_validates_project_document() -> None:
    config = validate_project_document(valid_document())

    assert config.project_id == "sample-project"
    assert config.repository.default_branch == "main"
    assert config.commands.test == ("python -m pytest",)
    assert config.pull_request.approvals_required == 1


def test_loads_repository_project_file(tmp_path: Path) -> None:
    directory = tmp_path / ".mde"
    directory.mkdir()
    path = directory / "project.yaml"
    path.write_text(
        """version: 1
project:
  id: sample-project
  name: Sample Project
repository:
  default_branch: main
  branch_pattern: "{type}/{assignee}/{task_id}"
commands:
  test: []
  build: []
""",
        encoding="utf-8",
    )

    config = load_project_config(tmp_path)

    assert config.source_path == path
    assert config.repository.protected_branches == ("main",)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda document: document["project"].update({"id": "bad project"}),
            "project.id",
        ),
        (
            lambda document: document["repository"].update(
                {"branch_pattern": "{type}/{task_id}"}
            ),
            "{assignee}",
        ),
        (
            lambda document: document["commands"].update({"test": "pytest"}),
            "commands.test",
        ),
    ],
)
def test_rejects_invalid_project_fields(mutate, message: str) -> None:
    document = valid_document()
    mutate(document)

    with pytest.raises(ProjectConfigError, match=message):
        validate_project_document(document)


def test_missing_project_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ProjectConfigError, match="not found"):
        load_project_config(tmp_path)
