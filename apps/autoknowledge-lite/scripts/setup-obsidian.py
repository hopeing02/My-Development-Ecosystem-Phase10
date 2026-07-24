from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autoknowledge_lite.obsidian_setup import setup_obsidian


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(
        description="Configure Obsidian core plugins, graph, templates and Bases.",
    )
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag only a preview is printed.",
    )
    args = parser.parse_args()

    vault = args.vault.expanduser().resolve()
    try:
        changed = setup_obsidian(vault, apply=args.apply)
    except ValueError as error:
        parser.error(str(error))

    mode = "APPLY" if args.apply else "PREVIEW"
    print(f"{mode}: changed={len(changed)}")
    for path in changed:
        print(path.relative_to(vault).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
