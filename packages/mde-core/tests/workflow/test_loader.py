from pathlib import Path

import pytest

from mde.workflow.loader import list_workflows, load_named_workflow, load_workflow
from mde.workflow.validator import WorkflowValidationError


def test_lists_bundled_workflows(tmp_path: Path) -> None:
    names = [item.name for item in list_workflows(tmp_path)]
    assert names == ["bugfix", "docs", "feature", "refactor"]


def test_repository_workflow_overrides_bundled_workflow(tmp_path: Path) -> None:
    directory = tmp_path / "workflows"
    directory.mkdir()
    (directory / "docs.yaml").write_text(
        "version: 1\nname: docs\ndescription: Local docs\nsteps:\n  - id: local\n    command: task.prepare\n",
        encoding="utf-8",
    )
    workflow = load_named_workflow("docs", tmp_path)
    assert workflow.description == "Local docs"
    assert workflow.source_path == (directory / "docs.yaml").resolve()


def test_rejects_dependency_on_later_step(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        "version: 1\nname: bad\nsteps:\n  - id: first\n    command: task.prepare\n    depends_on: [later]\n  - id: later\n    command: task.complete\n",
        encoding="utf-8",
    )
    with pytest.raises(WorkflowValidationError):
        load_workflow(path)
