"""Record, supplement, and view actual work in the existing daily Markdown log.

Only explicit record/amend actions write files. An amendment appends new
information and preserves the original. This tool never runs tasks or Git.
"""

from __future__ import annotations

import argparse
from datetime import date
import os
from pathlib import Path
import re
import sys
import tempfile

if __package__:
    from . import mde_daily_plan as daily_plan
else:
    import mde_daily_plan as daily_plan

RECORD_PREFIX = "- [D2 실적]"
HEADINGS = ("오늘 작업", "문제점", "해결", "내일 작업", "소요시간")
HEADING_PATTERN = re.compile(r"^## ([^\r\n]+?)[ \t]*(?=\r?$)", re.MULTILINE)


def record_work(
    root: Path,
    day: str,
    project: str,
    step: str,
    work: str,
    result: str,
    minutes: int | None,
    verification: str,
    evidence: str = "",
    problem: str = "",
    solution: str = "",
    next_work: str = "",
    *,
    supplement: bool = False,
) -> Path:
    """Add actual work, or append a correction without replacing its history."""
    root = root.resolve()
    day = daily_plan.validate_day(day)
    project = project.strip()
    projects = set(daily_plan.list_app_projects(root))
    core = root / "packages" / "mde-core"
    if core.is_dir() and core.resolve().is_relative_to(root):
        projects.add("mde-core")
    if project not in projects:
        raise ValueError(f"Phase10 저장소의 개발 대상이 아닙니다: {project}")
    if not daily_plan.STEP_PATTERN.fullmatch(step):
        raise ValueError("STEP 형식이 잘못되었습니다.")
    if minutes is not None and (type(minutes) is not int or not 1 <= minutes <= 720):
        raise ValueError("실제 소요시간은 1~720분 또는 미계측이어야 합니다.")
    if verification not in ("미검증", "검증완료", "검증실패"):
        raise ValueError("검증 상태는 미검증/검증완료/검증실패 중 하나여야 합니다.")
    if type(supplement) is not bool:
        raise ValueError("보완 여부는 명시적인 참/거짓이어야 합니다.")
    values = {
        "작업내용": work,
        "실행결과": result,
        "검증근거": evidence,
        "문제점": problem,
        "해결": solution,
        "내일 작업": next_work,
    }
    for label, raw in values.items():
        if (
            not isinstance(raw, str)
            or raw != raw.strip()
            or len(raw) > 250
            or any(ord(char) < 32 or char in "|`\x7f\x85\u2028\u2029" for char in raw)
        ):
            raise ValueError(
                f"{label}: 공백·제어문자·줄바꿈·구분자·250자 초과를 확인하세요."
            )
    if not work or not result:
        raise ValueError("실제 작업내용과 실행결과를 입력해야 합니다.")
    if verification != "미검증" and not evidence:
        raise ValueError(
            "검증완료/검증실패에는 사람이 확인한 실제 검증근거가 필요합니다."
        )

    path = daily_plan.daily_log_path(root, day)
    if path.is_symlink() or not path.parent.resolve().is_relative_to(root):
        raise ValueError("연결된 일지 파일이나 저장소 외부 경로는 사용할 수 없습니다.")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix(".md.d1-lock")
    try:
        lock.touch(exist_ok=False)
    except FileExistsError as error:
        raise ValueError(
            "이 날짜의 기록 작업이 진행 중이거나 잠금 파일이 남아 있습니다."
        ) from error
    try:
        existed = path.is_file()
        if existed:
            before = path.read_bytes()
            original = before.decode("utf-8")
        elif not path.exists():
            before = b""
            original = (
                f"# {day}\n\n" + "\n\n".join(f"## {name}" for name in HEADINGS) + "\n"
            )
        else:
            raise ValueError("일지 경로가 일반 파일이 아닙니다.")
        headers = list(HEADING_PATTERN.finditer(original))
        if tuple(match.group(1) for match in headers) != HEADINGS:
            raise ValueError(
                "기존 개발일지의 다섯 표준 제목과 순서를 확인할 수 없습니다."
            )
        identity = f"프로젝트: `{project}` | STEP: `{step}` |"
        base = f"{RECORD_PREFIX} {identity}"
        if not supplement and base in original:
            raise ValueError("같은 날짜·프로젝트·STEP의 실적은 이미 기록되어 있습니다.")
        if supplement and base not in original:
            raise ValueError(
                "보완할 원본 D2 실적이 없습니다. 먼저 record로 입력하세요."
            )
        prefix = "- [D2 보완]" if supplement else RECORD_PREFIX
        entry = (
            f"{prefix} {identity} 작업: {work} | 결과: {result} | 검증: {verification}"
        )
        if evidence:
            entry += f" | 근거: {evidence}"
        measured = f"{minutes}분" if minutes is not None else "미계측"
        tag = "D2 보완" if supplement else "D2"
        inserts = {
            "오늘 작업": entry,
            "소요시간": f"- [{tag} 시간] {identity} 실제: {measured}",
        }
        for heading, label, value in (
            ("문제점", "문제", problem),
            ("해결", "해결", solution),
            ("내일 작업", "다음", next_work),
        ):
            if value:
                inserts[heading] = f"- [{tag} {label}] {identity} {value}"
        if supplement:
            inserts = {
                heading: line
                for heading, line in inserts.items()
                if line not in original.splitlines()
            }
            if not inserts:
                raise ValueError("동일한 보완 내용이 이미 기록되어 있습니다.")

        newline = "\r\n" if "\r\n" in original else "\n"
        updated = original
        for header in reversed(headers):
            if header.group(1) in inserts:
                tail = updated[header.end() :]
                updated = (
                    updated[: header.end()]
                    + newline
                    + inserts[header.group(1)]
                    + (tail or newline)
                )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=".mde-d2-",
                suffix=".tmp",
                dir=path.parent,
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(updated.encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            if (existed and path.read_bytes() != before) or (
                not existed and path.exists()
            ):
                raise ValueError(
                    "저장 전 일지가 변경되었습니다. 다시 조회한 뒤 입력하세요."
                )
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        lock.unlink()
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase10 실제 개발일지 입력·저장·조회·보완"
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    actions = parser.add_subparsers(dest="action", required=True)
    for action, help_text in (
        ("record", "실제 개발실적 1건 저장"),
        ("amend", "원문을 보존하며 기록 보완"),
    ):
        record = actions.add_parser(action, help=help_text)
        record.add_argument("--date", default=date.today().isoformat())
        record.add_argument("--project", required=True)
        record.add_argument("--step", required=True)
        record.add_argument("--work", required=True)
        record.add_argument("--result", required=True)
        record.add_argument("--minutes", type=int)
        record.add_argument("--verification", default="미검증")
        record.add_argument("--evidence", default="")
        record.add_argument("--problem", default="")
        record.add_argument("--solution", default="")
        record.add_argument("--next", dest="next_work", default="")
    show = actions.add_parser("show", help="날짜별 개발일지 전체 조회")
    show.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        day = daily_plan.validate_day(args.date)
        if args.action in ("record", "amend"):
            path = record_work(
                root,
                day,
                args.project,
                args.step,
                args.work,
                args.result,
                args.minutes,
                args.verification,
                args.evidence,
                args.problem,
                args.solution,
                args.next_work,
                supplement=args.action == "amend",
            )
            print(
                f"실제 개발일지 {'보완' if args.action == 'amend' else '저장'}: {path.relative_to(root)}"
            )
        else:
            path = daily_plan.daily_log_path(root, day)
            if path.is_symlink() or not path.parent.resolve().is_relative_to(root):
                raise ValueError("잘못된 일지 경로입니다.")
            if not path.exists():
                print(f"{day}: 개발일지가 없습니다.")
            elif not path.is_file():
                raise ValueError("일지 경로가 일반 파일이 아닙니다.")
            else:
                print(path.read_text(encoding="utf-8"), end="")
    except (OSError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
