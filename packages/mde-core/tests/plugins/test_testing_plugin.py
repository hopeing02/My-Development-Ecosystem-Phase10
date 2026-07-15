import sys
from pathlib import Path

import pytest

from mde.plugins.builtin.testing import TestExecutionError, run_tests
from mde.workflow.models import WorkflowContext, WorkflowStep


def context(root: Path) -> WorkflowContext:
    return WorkflowContext(workflow_name="test", repository_root=root, task_id="TASK-TEST")


def test_testing_plugin_runs_command_and_writes_log(tmp_path: Path) -> None:
    step = WorkflowStep(
        id="test",
        command="test.run",
        args={"command": [sys.executable, "-c", "print('2 passed')"]},
    )
    result = run_tests(context(tmp_path), step)
    assert result["return_code"] == 0
    assert result["passed"] == 2
    assert Path(result["log_path"]).is_file()


def test_testing_plugin_raises_on_failure(tmp_path: Path) -> None:
    step = WorkflowStep(
        id="test",
        command="test.run",
        args={"command": [sys.executable, "-c", "raise SystemExit(3)"]},
    )
    with pytest.raises(TestExecutionError, match="exit code 3"):
        run_tests(context(tmp_path), step)
