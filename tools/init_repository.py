#!/usr/bin/env python3
"""Initialize the MDE monorepo baseline from the repository's tools folder."""

from __future__ import annotations

import argparse
from pathlib import Path

from mde_toolkit import initialize_repository


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MDE 저장소의 기본 폴더와 문서 체계를 생성합니다."
    )
    parser.add_argument(
        "--root", type=Path, default=default_root(), help="MDE 저장소 루트 경로"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="생성기가 관리하는 템플릿 파일을 덮어씁니다.",
    )
    args = parser.parse_args()

    results = initialize_repository(args.root, force=args.force)
    changed = [item for item in results if item.action != "skipped"]
    print(f"MDE 초기화 완료: {args.root.expanduser().resolve()}")
    print(f"생성 또는 갱신: {len(changed)}개, 유지: {len(results) - len(changed)}개")
    for item in changed:
        print(
            f"  [{item.action}] {item.path.relative_to(args.root.expanduser().resolve())}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
