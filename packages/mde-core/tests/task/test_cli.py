from pathlib import Path

from mde.cli import main


def write_task(root: Path):
    path = root / "tasks" / "pending" / "TASK-001.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "version: 1\ntask:\n  id: TASK-001\n  type: docs\n  title: Update README\n  workflow: docs\n",
        encoding="utf-8",
    )


def test_task_list_and_show(tmp_path: Path, monkeypatch, capsys):
    write_task(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["task", "list"]) == 0
    assert "TASK-001" in capsys.readouterr().out
    assert main(["task", "show", "TASK-001"]) == 0
    assert "Status: pending" in capsys.readouterr().out


def test_task_run(tmp_path: Path, monkeypatch, capsys):
    write_task(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert main(["task", "run", "TASK-001"]) == 0
    assert "Task completed" in capsys.readouterr().out
