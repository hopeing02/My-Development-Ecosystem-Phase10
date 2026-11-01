"""Link an existing YAML TaskStore outcome to one actual D2 work record.

Preview is read-only. --write adds one sanitized reference without running
tasks, modifying task state, or changing the D2 verification verdict.
"""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import sys
import tempfile

import yaml

if __package__:
    from . import mde_daily_log as daily_log
    from . import mde_daily_plan as daily_plan
else:
    import mde_daily_log as daily_log
    import mde_daily_plan as daily_plan

LINK_PREFIX = "- [D3 연동]"
MAX_RESULT_BYTES = 1_000_000


def link_task_result(
    root: Path, day: str, project: str, step: str, task_id: str, write: bool = False
) -> str:
    """Preview or append a stored execution reference to an actual work log."""
    from mde.task.loader import load_task
    from mde.task.store import TaskDirectories, TaskStore

    root = root.resolve()
    day = daily_plan.validate_day(day)
    project = project.strip()
    projects = set(daily_plan.list_app_projects(root))
    core = root / "packages" / "mde-core"
    if core.is_dir() and core.resolve().is_relative_to(root):
        projects.add("mde-core")
    if project not in projects:
        raise ValueError("Phase10에 등록된 프로젝트가 아닙니다.")
    if not daily_plan.STEP_PATTERN.fullmatch(
        step
    ) or not daily_plan.STEP_PATTERN.fullmatch(task_id):
        raise ValueError("STEP 또는 Task ID 형식이 잘못되었습니다.")
    if type(write) is not bool:
        raise ValueError("write는 명시적인 참/거짓이어야 합니다.")

    path = daily_plan.daily_log_path(root, day)
    if path.is_symlink() or not path.parent.resolve().is_relative_to(root):
        raise ValueError("허용되지 않은 개발일지 경로입니다.")
    if not path.is_file():
        raise ValueError("해당 날짜의 D2 실제 개발일지가 없습니다.")
    original_bytes = path.read_bytes()
    original = original_bytes.decode("utf-8")
    headers = list(daily_log.HEADING_PATTERN.finditer(original))
    if tuple(match.group(1) for match in headers) != daily_log.HEADINGS:
        raise ValueError("기존 개발일지의 표준 제목과 순서를 확인할 수 없습니다.")
    identity = f"{daily_log.RECORD_PREFIX} 프로젝트: `{project}` | STEP: `{step}` |"
    today = original[headers[0].end() : headers[1].start()]
    if (
        sum(line.startswith(identity) for line in today.splitlines()) != 1
        or sum(line.startswith(identity) for line in original.splitlines()) != 1
    ):
        raise ValueError("오늘 작업의 연결 대상 D2 실적이 정확히 1건이어야 합니다.")

    tasks = root / "tasks"
    if not tasks.is_dir() or tasks.resolve() != tasks:
        raise ValueError("실제 TaskStore 작업 폴더가 없거나 연결된 경로입니다.")
    directories = {
        name: tasks / name for name in ("pending", "processing", "completed", "failed")
    }
    for directory in directories.values():
        if directory.resolve() != directory or (
            directory.exists() and not directory.is_dir()
        ):
            raise ValueError("TaskStore 상태 폴더 경로가 허용 범위 밖입니다.")
        for candidate in directory.glob("*.yaml"):
            if candidate.is_symlink() or candidate.resolve().parent != directory:
                raise ValueError("Task 또는 결과 YAML 경로가 허용 범위 밖입니다.")

    # The normal constructor creates directories. Bind only the existing public
    # state needed by find(), so this lookup does not create or alter task state.
    store = TaskStore.__new__(TaskStore)
    store.repository_root = root
    store.root = tasks
    store.dirs = TaskDirectories(**directories)
    found = store.find(task_id)
    if found is None:
        raise ValueError("실제 TaskStore에서 해당 Task ID를 찾지 못했습니다.")
    status, task_path = found
    if status not in ("completed", "failed"):
        raise ValueError(f"아직 종료되지 않은 Task입니다: {status}")
    if task_path.is_symlink() or task_path.resolve().parent != directories[status]:
        raise ValueError("Task 파일 경로가 허용 범위 밖입니다.")
    task_before = task_path.read_bytes()
    try:
        task = load_task(task_path)
    except (ValueError, RecursionError) as error:
        raise ValueError("Task 정의 YAML이 올바르지 않습니다.") from error
    if task.task_id != task_id:
        raise ValueError("Task 파일과 입력 ID가 일치하지 않습니다.")
    project_tags = [
        task.metadata[key] for key in ("project", "project_id") if key in task.metadata
    ]
    step_tags = [
        task.metadata[key] for key in ("step", "step_id") if key in task.metadata
    ]
    if any(value != project for value in project_tags):
        raise ValueError("Task의 프로젝트 메타데이터가 D2 실적과 다릅니다.")
    if any(value != step for value in step_tags):
        raise ValueError("Task의 STEP 메타데이터가 D2 실적과 다릅니다.")

    result_path = task_path.parent / f"{task_id}.result.yaml"
    if (
        result_path.is_symlink()
        or result_path.resolve().parent != directories[status]
        or not result_path.is_file()
    ):
        raise ValueError("실제 Task 결과 YAML이 없거나 경로가 올바르지 않습니다.")
    with result_path.open("rb") as handle:
        encoded = handle.read(MAX_RESULT_BYTES + 1)
    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError("실행 결과 YAML 용량이 허용 범위를 초과했습니다.")
    try:
        document = yaml.safe_load(encoded.decode("utf-8"))
    except (yaml.YAMLError, UnicodeError, RecursionError) as error:
        raise ValueError("실행 결과 YAML을 읽을 수 없습니다.") from error
    if not isinstance(document, dict) or not isinstance(document.get("result"), dict):
        raise ValueError("실행 결과 YAML 구조가 올바르지 않습니다.")
    result = document["result"]
    if (
        result.get("task_id") != task_id
        or result.get("workflow") != task.workflow
        or result.get("status") != status
    ):
        raise ValueError("Task 정의와 실행 결과의 식별정보가 일치하지 않습니다.")
    steps = result.get("steps")
    if not isinstance(steps, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("command"), str)
        and bool(item["command"].strip())
        and item.get("status") in ("completed", "failed", "skipped")
        for item in steps
    ):
        raise ValueError("실행 결과 단계 목록이나 상태가 올바르지 않습니다.")
    tests = [item["status"] for item in steps if item["command"] == "test.run"]
    if "failed" in tests:
        test_state = "실패 기록"
    elif "skipped" in tests:
        test_state = "생략 기록"
    elif tests:
        test_state = "단계 완료 기록(검증 근거 별도)"
    else:
        test_state = "test.run 기록 없음"
    matching = "메타데이터 일치" if project_tags and step_tags else "사용자 지정 연결"
    entry = (
        f"{LINK_PREFIX} 프로젝트: `{project}` | STEP: `{step}` | "
        f"TaskId: `{task_id}` | Task: {status} | test.run: {test_state} | 연결: {matching}"
    )
    if not write:
        return entry

    lock = path.with_suffix(".md.d1-lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "이 날짜의 기록 작업이 진행 중이거나 잠금 파일이 남아 있습니다."
        ) from error
    try:
        if path.read_bytes() != original_bytes:
            raise ValueError("조회 이후 개발일지가 변경되었습니다. 다시 확인하세요.")
        if any(
            line.startswith(LINK_PREFIX) and f"TaskId: `{task_id}` |" in line
            for line in original.splitlines()
        ):
            raise ValueError("이 날짜의 개발일지에 같은 Task가 이미 연결되어 있습니다.")
        header = headers[0]
        newline = "\r\n" if "\r\n" in original else "\n"
        updated = original[: header.end()] + newline + entry + original[header.end() :]
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".mde-d3-",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(updated.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            if path.read_bytes() != original_bytes:
                raise ValueError("저장 전 개발일지가 변경되었습니다. 다시 확인하세요.")
            if (
                store.find(task_id) != found
                or task_path.read_bytes() != task_before
                or result_path.read_bytes() != encoded
            ):
                raise ValueError("조회 이후 Task 또는 실행 결과가 변경되었습니다.")
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        lock.unlink()
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase10 실제 TaskStore 실행결과를 D2 일지에 연결"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--project", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument(
        "--write", action="store_true", help="확인한 결과를 개발일지에 기록"
    )
    args = parser.parse_args(argv)
    try:
        print(
            link_task_result(
                args.root, args.date, args.project, args.step, args.task_id, args.write
            )
        )
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
