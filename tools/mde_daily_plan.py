"""Manage a single daily development plan for existing MDE app projects."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import os
import re
import sys
import tempfile

PLAN_PREFIX = "- [D1 계획]"
STEP_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
TODAY_SECTION = re.compile(r"^## 오늘 작업[ \t]*(?=\r?$)", re.MULTILINE)


def list_app_projects(root: Path) -> list[str]:
    """List real applications, excluding the checked-in scaffold project."""
    apps_dir = root / "apps"
    if not apps_dir.is_dir():
        raise ValueError(f"프로젝트 폴더가 없습니다: {apps_dir}")
    if not apps_dir.resolve().is_relative_to(root.resolve()):
        raise ValueError("프로젝트 폴더가 저장소 밖을 가리킵니다.")
    return sorted(
        app.name
        for app in apps_dir.iterdir()
        if app.is_dir()
        and not app.is_symlink()
        and app.resolve() == apps_dir.resolve() / app.name
        and app.name != "sample-project"
    )


def validate_day(day: str) -> str:
    if not DATE_PATTERN.fullmatch(day):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(day).isoformat()
    except ValueError as error:
        raise ValueError("유효하지 않은 날짜입니다.") from error


def daily_log_path(root: Path, day: str) -> Path:
    day = validate_day(day)
    path = root / "docs" / "14_operations" / "DevelopmentLog" / f"{day}.md"
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("개발일지 경로가 저장소 밖을 가리킵니다.")
    return path


def register_plan(
    root: Path, day: str, project: str, step: str, goal: str, minutes: int
) -> Path:
    path = daily_log_path(root, day)
    names = list_app_projects(root)
    project = project.strip()
    if project not in names:
        raise ValueError(f"저장소에 없는 앱 프로젝트입니다: {project}")
    if not STEP_PATTERN.fullmatch(step):
        raise ValueError("STEP은 영문·숫자·점·밑줄·하이픈으로만 작성합니다.")
    if any(ord(char) < 32 or char in "\x7f\x85\u2028\u2029" for char in goal):
        raise ValueError("목표는 제어문자나 줄바꿈 없는 문장이어야 합니다.")
    goal = goal.strip()
    if not goal or len(goal) > 200:
        raise ValueError("목표는 줄바꿈 없는 1~200자 문장이어야 합니다.")
    if type(minutes) is not int or not 15 <= minutes <= 720:
        raise ValueError("예정 시간은 15~720분 사이여야 합니다.")

    entry = (
        f"{PLAN_PREFIX} 프로젝트: `{project}` | STEP: `{step}` | "
        f"목표: {goal} | 예정: {minutes}분 | 상태: 계획"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".md.d1-lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "이 날짜의 계획 등록이 진행 중이거나 잠금 파일이 남아 있습니다."
        ) from error
    try:
        if path.exists():
            original = path.read_bytes().decode("utf-8")
            if PLAN_PREFIX in original:
                raise ValueError(
                    "이 날짜에는 D1 계획이 이미 있습니다. 기존 기록을 보호합니다."
                )
            match = TODAY_SECTION.search(original)
            if match is None:
                raise ValueError("기존 개발일지에 '## 오늘 작업' 제목이 없습니다.")
            newline = "\r\n" if "\r\n" in original else "\n"
            updated = (
                original[: match.end()]
                + newline
                + entry
                + (original[match.end() :] or newline)
            )
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=f".{path.name}.",
                    suffix=".tmp",
                    dir=path.parent,
                    delete=False,
                ) as handle:
                    temporary = Path(handle.name)
                    handle.write(updated.encode("utf-8"))
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
        else:
            content = (
                f"# {day}\n\n## 오늘 작업\n{entry}\n\n"
                "## 문제점\n- 미기록\n\n"
                "## 해결\n- 미기록\n\n"
                "## 내일 작업\n- 미정\n\n"
                f"## 소요시간\n- 예정: {minutes}분\n- 실제: 미계측\n"
            )
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    finally:
        lock.unlink()
    return path


def show_plan(root: Path, day: str) -> str:
    path = daily_log_path(root, day)
    if not path.is_file():
        return f"{day}: 등록된 개발일지가 없습니다."
    lines = path.read_text(encoding="utf-8").splitlines()
    plans = [line for line in lines if line.startswith(PLAN_PREFIX)]
    return "\n".join(plans) if plans else f"{day}: D1 개발계획이 없습니다."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MDE 저장소 앱 프로젝트의 일일 개발계획"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("projects", help="실제 앱 프로젝트 목록")
    plan = actions.add_parser("plan", help="오늘의 개발계획 1건 등록")
    plan.add_argument("--project", required=True)
    plan.add_argument("--step", required=True)
    plan.add_argument("--goal", required=True)
    plan.add_argument("--minutes", type=int, default=120)
    plan.add_argument("--date", default=date.today().isoformat())
    show = actions.add_parser("show", help="날짜별 계획 조회")
    show.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.action == "projects":
            for project in list_app_projects(root):
                print(project)
        elif args.action == "plan":
            output = register_plan(
                root, args.date, args.project, args.step, args.goal, args.minutes
            )
            print(f"개발계획 등록: {output.relative_to(root)}")
        else:
            print(show_plan(root, args.date))
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
