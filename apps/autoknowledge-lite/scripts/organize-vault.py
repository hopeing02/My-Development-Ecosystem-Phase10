from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from autoknowledge_lite.knowledge_graph import (
    FOLDER_MOCS,
    MOC_HOME,
    PRIMARY_MOCS,
    note_content_length,
    note_stem,
    note_title,
    organize_note,
)

EXCLUDED_PARTS = {".git", ".obsidian", ".trash"}
HOME_CONTENT = """# Personal Knowledge Home

## 주제 지도

- [[MOC - AutoKnowledge]]
- [[MOC - 로컬 AI와 스마트홈]]
- [[MOC - Android 개발]]
- [[MOC - 생활과 요리]]

## 운영

- 새 자료는 먼저 `00_Inbox`와 `status: to-review`로 확인합니다.
- 주제 노트의 Backlinks에서 연결된 자료를 탐색합니다.
"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(
        description="Add deterministic Obsidian metadata and MOC links.",
    )
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag only a preview is printed.",
    )
    args = parser.parse_args()

    vault = args.vault.expanduser().resolve()
    if not vault.is_dir() or not (vault / ".git").is_dir():
        parser.error("vault must be an existing Git Vault directory")

    notes = _content_notes(vault)
    duplicate_info = _duplicate_candidates(notes)
    changed: list[Path] = []
    for path in notes:
        original = path.read_text(encoding="utf-8")
        canonical, status = duplicate_info.get(path, (None, None))
        updated = organize_note(
            original,
            folder=path.parent.name,
            canonical=canonical,
            duplicate_status=status,
        )
        if updated == original:
            continue
        changed.append(path)
        if args.apply:
            path.write_text(updated, encoding="utf-8")

    created = _ensure_hubs(vault, apply=args.apply)
    mode = "APPLY" if args.apply else "PREVIEW"
    print(f"{mode}: notes={len(notes)} changed={len(changed)} hubs={len(created)}")
    for path in (*changed, *created):
        print(path.relative_to(vault).as_posix())
    return 0


def _content_notes(vault: Path) -> list[Path]:
    return sorted(
        path
        for path in vault.rglob("*.md")
        if not EXCLUDED_PARTS.intersection(path.relative_to(vault).parts)
        and path.name != "README.md"
        and path.name != f"{MOC_HOME}.md"
        and not path.name.startswith("MOC - ")
    )


def _duplicate_candidates(
    notes: list[Path],
) -> dict[Path, tuple[str | None, str | None]]:
    by_title: dict[str, list[Path]] = defaultdict(list)
    for path in notes:
        by_title[note_title(path.read_text(encoding="utf-8"))].append(path)

    result: dict[Path, tuple[str | None, str | None]] = {}
    for candidates in by_title.values():
        if len(candidates) < 2:
            continue
        canonical = max(
            candidates,
            key=lambda item: (
                note_content_length(item.read_text(encoding="utf-8")),
                item.as_posix().casefold(),
            ),
        )
        for path in candidates:
            if path == canonical:
                continue
            result[path] = (note_stem(canonical), "possible-duplicate")
    return result


def _ensure_hubs(vault: Path, *, apply: bool) -> list[Path]:
    contents = {MOC_HOME: HOME_CONTENT}
    all_mocs = tuple(dict.fromkeys((*PRIMARY_MOCS, *FOLDER_MOCS.values())))
    for moc in all_mocs:
        contents[moc] = (
            f"# {moc.removeprefix('MOC - ')}\n\n"
            f"상위 지도: [[{MOC_HOME}]]\n\n"
            "## 연결된 노트\n\n"
            "이 노트를 가리키는 Backlinks에서 관련 자료를 확인합니다.\n"
        )

    created: list[Path] = []
    for name, content in contents.items():
        destination = vault / f"{name}.md"
        if destination.exists():
            continue
        created.append(destination)
        if apply:
            destination.write_text(content, encoding="utf-8")
    return created


if __name__ == "__main__":
    raise SystemExit(main())
