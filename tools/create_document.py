#!/usr/bin/env python3
"""Create a governed MDE document from a template."""

from __future__ import annotations

import argparse
from pathlib import Path

from mde_toolkit import create_document


def default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="MDE 표준 문서를 생성합니다.")
    parser.add_argument(
        "--category",
        required=True,
        help="con, gov, std, dev, cmd, prm, arch, sds, adr, qa, code, test, release, ops",
    )
    parser.add_argument("--id", required=True, dest="document_id", help="예: SDS-002")
    parser.add_argument("--title", required=True, help="문서 제목")
    parser.add_argument(
        "--project", help="프로젝트 SDS 또는 설계 문서로 만들 때의 프로젝트명"
    )
    parser.add_argument(
        "--root", type=Path, default=default_root(), help="MDE 저장소 루트 경로"
    )
    parser.add_argument(
        "--force", action="store_true", help="같은 문서가 있으면 덮어씁니다."
    )
    args = parser.parse_args()

    try:
        result = create_document(
            args.root,
            args.category,
            args.document_id,
            args.title,
            project=args.project,
            force=args.force,
        )
    except ValueError as error:
        parser.error(str(error))

    print(
        f"[{result.action}] {result.path.relative_to(args.root.expanduser().resolve())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
