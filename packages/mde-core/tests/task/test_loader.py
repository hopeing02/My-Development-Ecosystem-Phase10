from pathlib import Path

import pytest

from mde.task.loader import TaskValidationError, load_task, validate_task_document


def valid_document():
    return {
        "version": 1,
        "task": {
            "id": "TASK-001",
            "type": "docs",
            "title": "Update README",
            "description": "Add workflow usage.",
            "workflow": "docs",
            "source": "mobile",
            "execution": {"run_tests": True},
            "acceptance": ["README updated"],
        },
    }


def test_validate_task_document():
    task = validate_task_document(valid_document())
    assert task.task_id == "TASK-001"
    assert task.workflow == "docs"
    assert task.execution.run_tests is True


def test_load_task_records_source_path(tmp_path: Path):
    path = tmp_path / "TASK-001.yaml"
    path.write_text(
        "version: 1\ntask:\n  id: TASK-001\n  type: docs\n  title: Update README\n  workflow: docs\n",
        encoding="utf-8",
    )
    task = load_task(path)
    assert task.source_path == path.resolve()


def test_missing_required_field_is_rejected():
    document = valid_document()
    del document["task"]["workflow"]
    with pytest.raises(TaskValidationError):
        validate_task_document(document)
