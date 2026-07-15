from mde.git.branches import branch_name_for_task


def test_branch_name_for_task_is_safe() -> None:
    assert branch_name_for_task("TASK 001", "Feature") == "feature/task-001"
