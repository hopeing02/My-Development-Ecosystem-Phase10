#!/usr/bin/env python3
"""Create an MDE application and its central project document tree."""

from __future__ import annotations

import argparse
from pathlib import Path

from mde_toolkit import create_project


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="MDE 새 프로젝트를 생성합니다.")
    parser.add_argument(
        "--name", required=True, help="kebab-case 프로젝트명. 예: senior-matching"
    )
    parser.add_argument(
        "--type",
        default="generic",
        choices=("generic", "python", "gas", "nextjs"),
        help="프로젝트 기술 유형",
    )
    parser.add_argument(
        "--root", type=Path, default=default_root(), help="MDE 저장소 루트 경로"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="생성기가 관리하는 프로젝트 템플릿을 덮어씁니다.",
    )
    args = parser.parse_args()

    try:
        results = create_project(args.root, args.name, args.type, force=args.force)
    except ValueError as error:
        parser.error(str(error))

    root = args.root.expanduser().resolve()
    changed = [item for item in results if item.action != "skipped"]
    print(f"프로젝트 생성 완료: {args.name}")
    print(f"생성 또는 갱신: {len(changed)}개, 유지: {len(results) - len(changed)}개")
    for item in changed:
        print(f"  [{item.action}] {item.path.relative_to(root)}")
    print(f"앱 코드: apps/{args.name}/")
    print(f"프로젝트 문서: docs/15_projects/{args.name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
