from mde.cli import main


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
