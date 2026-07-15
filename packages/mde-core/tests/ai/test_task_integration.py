from pathlib import Path

import yaml

from mde.task.executor import execute_task
from mde.task.loader import load_task
from mde.task.store import TaskStore


def test_task_generates_reviews_and_applies_mock_artifact(tmp_path: Path) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    (workflows / "feature.yaml").write_text(
        """version: 1
name: feature
description: integration
steps:
  - id: generate
    command: ai.generate
  - id: review
    command: change.review
    depends_on: [generate]
  - id: apply
    command: change.apply
    depends_on: [review]
""",
        encoding="utf-8",
    )
    pending = tmp_path / "tasks/pending"
    pending.mkdir(parents=True)
    task_path = pending / "TASK-AI.yaml"
    task_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "task": {
                    "id": "TASK-AI",
                    "type": "feature",
                    "title": "Generate file",
                    "description": "Create generated.txt",
                    "workflow": "feature",
                    "execution": {"auto_apply": True, "run_tests": False},
                    "inputs": {
                        "ai": {
                            "provider": "mock",
                            "artifacts": [
                                {"path": "generated.txt", "content": "from mobile task"}
                            ],
                        }
                    },
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = execute_task(load_task(task_path), tmp_path, store=TaskStore(tmp_path))

    assert result.status == "completed"
    assert (tmp_path / "generated.txt").read_text() == "from mobile task"
    assert (tmp_path / "tasks/completed/TASK-AI.result.yaml").is_file()
