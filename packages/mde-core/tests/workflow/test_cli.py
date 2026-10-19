from mde.cli import main
from pathlib import Path

import pytest


def test_workflow_list(capsys) -> None:
    assert main(["workflow", "list"]) == 0
    assert "feature:" in capsys.readouterr().out


def test_workflow_show(capsys) -> None:
    assert main(["workflow", "show", "feature"]) == 0
    output = capsys.readouterr().out
    assert "Name: feature" in output
    assert "ai.generate" in output


def test_workflow_run(capsys) -> None:
    assert main(["workflow", "run", "docs", "--message", "README update"]) == 0
    output = capsys.readouterr().out
    assert "Workflow completed: docs" in output
    assert "[completed] complete" in output


@pytest.mark.parametrize("content", ["not-json", "[]", '{"push": "true"}'])
def test_workflow_rejects_invalid_inputs(tmp_path: Path, content: str, capsys) -> None:
    path = tmp_path / "inputs.json"
    path.write_text(content, encoding="utf-8")
    assert main(["workflow", "run", "feature-local", "--inputs", str(path)]) == 1
    assert "Workflow completed" not in capsys.readouterr().out


def test_automatic_repair_requires_runtime(capsys) -> None:
    assert main(["workflow", "run", "feature-local", "--max-fix-attempts", "1"]) == 1
    assert "requires --runtime" in capsys.readouterr().out


def test_local_deployment_workflow_dry_run_has_no_deployment_output(capsys) -> None:
    assert main(["workflow", "run", "feature-local"]) == 0
    output = capsys.readouterr().out
    assert "[completed] deploy: deploy.local" in output
    assert "Deployment URL:" not in output
