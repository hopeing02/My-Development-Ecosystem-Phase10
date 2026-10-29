"""Link a stored YAML task outcome to one D1 daily development plan.

Run with ``uv run python tools/mde_daily_result.py --task-id TASK-ID``.
Only --write changes the development log. TaskStore may create its missing
state directories even in preview mode. No task, result YAML, or D1 code is
changed. Recorded test.run completion is evidence, not a fresh test verdict.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import os
import re
import sys
import tempfile

import yaml

if __package__:
    from . import mde_daily_plan as daily_plan
else:
    import mde_daily_plan as daily_plan

RESULT_PREFIX = "- [D2 결과]"
PROJECT_PATTERN = re.compile(r"^- \[D1 계획\] 프로젝트: `([a-z][a-z0-9-]*)` \|")
MAX_RESULT_BYTES = 1_000_000


def link_task_result(root: Path, day: str, task_id: str, write: bool) -> str:
    """Inspect an existing task outcome and optionally add one log entry."""
    from mde.task.loader import load_task
    from mde.task.store import TaskStore

    root = root.resolve()
    day = daily_plan.validate_day(day)
    if not daily_plan.STEP_PATTERN.fullmatch(task_id):
        raise ValueError("작업 ID 형식이 올바르지 않습니다.")
    if type(write) is not bool:
        raise ValueError("write는 명시적인 참/거짓 값이어야 합니다.")

    plan = daily_plan.show_plan(root, day)
    if not plan.startswith(daily_plan.PLAN_PREFIX) or "\n" in plan:
        raise ValueError("해당 날짜에 D1 개발계획 1건이 필요합니다.")
    match = PROJECT_PATTERN.search(plan)
    if match is None or match.group(1) not in daily_plan.list_app_projects(root):
        raise ValueError("D1 계획의 프로젝트가 현재 apps 목록과 일치하지 않습니다.")
    project = match.group(1)

    # Check before TaskStore's constructor creates any state directories.
    for folder in ("", "pending", "processing", "completed", "failed"):
        if not (root / "tasks" / folder).resolve().is_relative_to(root):
            raise ValueError("TaskStore 경로가 저장소 밖을 가리킵니다.")
    store = TaskStore(root)
    located = store.find(task_id)
    if located is None:
        raise ValueError("MDE TaskStore에서 작업 ID를 찾지 못했습니다.")
    status, task_path = located
    if status not in ("completed", "failed"):
        raise ValueError(f"작업이 아직 종료되지 않았습니다: {status}")
    task_folder = (root / "tasks" / status).resolve()
    if task_path.resolve().parent != task_folder:
        raise ValueError("Task 파일이 해당 상태 폴더 밖을 가리킵니다.")

    task = load_task(task_path)
    if task.task_id != task_id:
        raise ValueError("Task YAML의 작업 ID가 요청한 ID와 불일치합니다.")
    if any(
        key in task.metadata and task.metadata[key] != project
        for key in ("project", "project_id")
    ):
        raise ValueError("Task 메타데이터의 프로젝트가 D1 계획과 다릅니다.")

    result_path = task_path.parent / f"{task_id}.result.yaml"
    if result_path.resolve().parent != task_folder:
        raise ValueError("Task 결과 파일이 해당 상태 폴더 밖을 가리킵니다.")
    if not result_path.is_file():
        raise ValueError("Task 실행 결과 YAML이 없습니다. 완료로 기록하지 않습니다.")
    with result_path.open("rb") as handle:
        encoded = handle.read(MAX_RESULT_BYTES + 1)
    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError("Task 실행 결과 파일이 너무 큽니다.")
    try:
        document = yaml.safe_load(encoded.decode("utf-8"))
    except (yaml.YAMLError, UnicodeError) as error:
        raise ValueError("Task 실행 결과 YAML 형식이 올바르지 않습니다.") from error
    if not isinstance(document, dict) or not isinstance(document.get("result"), dict):
        raise ValueError("Task 실행 결과 구조가 올바르지 않습니다.")
    result = document["result"]
    if (
        result.get("task_id") != task_id
        or result.get("status") != status
        or result.get("workflow") != task.workflow
    ):
        raise ValueError("Task 실행 결과의 ID, 상태 또는 Workflow가 불일치합니다.")

    steps = result.get("steps")
    if not isinstance(steps, list) or not all(
        isinstance(step, dict)
        and isinstance(step.get("command"), str)
        and bool(step["command"].strip())
        and step.get("status") in ("completed", "failed", "skipped")
        for step in steps
    ):
        raise ValueError("Task 결과의 단계 목록이 유효하지 않습니다.")
    tests = [step["status"] for step in steps if step["command"] == "test.run"]
    if "failed" in tests:
        verification = "test.run 실패"
    elif "skipped" in tests:
        verification = "test.run 일부 생략" if "completed" in tests else "test.run 생략"
    elif "completed" in tests:
        verification = "test.run 기록상 완료"
    else:
        verification = "test.run 결과 없음"

    entry = (
        f"{RESULT_PREFIX} 프로젝트: `{project}` | 작업ID: `{task_id}` | "
        f"Task: {status} | 검증: {verification}"
    )
    if not write:
        return entry

    log_path = daily_plan.daily_log_path(root, day)
    # Cooperate with the frozen D1 writer, without changing its implementation.
    lock = log_path.with_suffix(".md.d1-lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "이 날짜의 기록 작업이 진행 중이거나 잠금 파일이 남아 있습니다."
        ) from error
    try:
        original = log_path.read_bytes().decode("utf-8")
        if daily_plan.show_plan(root, day) != plan:
            raise ValueError(
                "D1 계획이 조회 이후 변경되었습니다. 다시 확인해야 합니다."
            )
        if RESULT_PREFIX in original:
            raise ValueError(
                "이미 D2 결과가 기록되어 있습니다. 기존 일지를 보호합니다."
            )
        header = daily_plan.TODAY_SECTION.search(original)
        if header is None:
            raise ValueError("기존 일지에 '## 오늘 작업' 제목이 없습니다.")
        newline = "\r\n" if "\r\n" in original else "\n"
        updated = (
            original[: header.end()]
            + newline
            + entry
            + (original[header.end() :] or newline)
        )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{log_path.name}.",
                suffix=".tmp",
                dir=log_path.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(updated.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, log_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        lock.unlink()
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MDE D1 계획과 기존 TaskStore 결과 연결"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--task-id", required=True)
    parser.add_argument(
        "--write", action="store_true", help="확인한 결과만 개발일지에 1회 기록"
    )
    args = parser.parse_args(argv)
    try:
        print(link_task_result(args.root, args.date, args.task_id, args.write))
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
