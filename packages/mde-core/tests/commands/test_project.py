from pathlib import Path
import sys

import pytest
import yaml

from mde.commands.project import (
    ProjectCommandError,
    parse_project_command,
    run_project_phase,
)


def write_project_config(
    root: Path, test_commands: list[str], build_commands: list[str]
) -> None:
    directory = root / ".mde"
    directory.mkdir()
    document = {
        "version": 1,
        "project": {"id": "sample", "name": "Sample"},
        "repository": {
            "default_branch": "main",
            "branch_pattern": "{type}/{assignee}/{task_id}",
        },
        "commands": {"test": test_commands, "build": build_commands},
    }
    (directory / "project.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False), encoding="utf-8"
    )


def test_runs_all_commands_in_declared_order(tmp_path: Path) -> None:
    marker = tmp_path / "marker.txt"
    first = f"{sys.executable} -c \"from pathlib import Path; Path('marker.txt').write_text('1')\""
    second = f"{sys.executable} -c \"from pathlib import Path; p=Path('marker.txt'); p.write_text(p.read_text()+'2')\""
    write_project_config(tmp_path, [first, second], [])

    results = run_project_phase(tmp_path, "test")

    assert len(results) == 2
    assert marker.read_text() == "12"


def test_stops_when_project_command_fails(tmp_path: Path) -> None:
    command = f'{sys.executable} -c "raise SystemExit(7)"'
    write_project_config(tmp_path, [], [command])

    with pytest.raises(ProjectCommandError, match="exit code 7"):
        run_project_phase(tmp_path, "build")


@pytest.mark.parametrize(
    "command", ["pytest && deploy", "pytest | deploy", "pytest\ndeploy"]
)
def test_rejects_shell_control_syntax(command: str) -> None:
    with pytest.raises(ProjectCommandError):
        parse_project_command(command)
