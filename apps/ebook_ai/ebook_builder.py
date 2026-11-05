"""Assemble a reviewed Markdown manuscript list into a table of contents and book."""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class EbookBuildError(ValueError):
    """Invalid manifest, manuscript, or output destination."""


@dataclass(frozen=True)
class BuildResult:
    toc_path: Path
    basic_path: Path
    chapter_count: int


def _title(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isprintable():
        raise EbookBuildError(f"{field}: non-empty, single-line text required")
    return value.strip()


def _markdown_text(value: str) -> str:
    # Escape labels so brackets, HTML, and formatting cannot break generated links.
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", html.escape(value))


def _read_manifest(manifest_path: Path) -> tuple[str, list[tuple[str, Path, str]]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EbookBuildError(
            f"Cannot read JSON manifest: {manifest_path}: {exc}"
        ) from exc
    if not isinstance(manifest, dict):
        raise EbookBuildError("Manifest must be a JSON object")
    title = _title(manifest.get("title"), "title")
    entries = manifest.get("chapters")
    if not isinstance(entries, list) or not entries:
        raise EbookBuildError("chapters: non-empty list required")

    chapters: list[tuple[str, Path, str]] = []
    seen: set[Path] = set()
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise EbookBuildError(f"chapters[{index}]: object required")
        chapter_title = _title(entry.get("title"), f"chapters[{index}].title")
        source_value = entry.get("path")
        if (
            not isinstance(source_value, str)
            or not source_value.strip()
            or "\0" in source_value
        ):
            raise EbookBuildError(f"chapters[{index}].path: non-empty path required")
        source = (manifest_path.parent / source_value).resolve()
        if source.suffix.lower() != ".md":
            raise EbookBuildError(f"Markdown (.md) manuscript required: {source}")
        try:
            body = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise EbookBuildError(f"Cannot read manuscript: {source}: {exc}") from exc
        if not body.strip():
            raise EbookBuildError(f"Empty manuscript: {source}")
        if source in seen or any(source.samefile(previous) for previous in seen):
            raise EbookBuildError(f"Duplicate manuscript: {source}")
        seen.add(source)
        chapters.append((chapter_title, source, body))
    return title, chapters


def build_ebook(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
) -> BuildResult:
    """Build toc.md/basic.md in manifest order after validating every manuscript.

    Paths in the manifest are relative to that manifest, never the working directory.
    Body text is preserved, except UTF-8 BOM removal and newline normalization to LF.
    Manuscript review/approval is the caller's responsibility.
    """
    manifest_path = Path(manifest_path).resolve()
    title, chapters = _read_manifest(manifest_path)
    output_dir = Path(output_dir).resolve()
    outputs = (output_dir / "toc.md", output_dir / "basic.md")
    if all(target.exists() for target in outputs) and outputs[0].samefile(outputs[1]):
        raise EbookBuildError("Output files must be distinct files")
    inputs = [manifest_path, *(source for _, source, _ in chapters)]
    for target in outputs:
        if target.is_symlink():
            raise EbookBuildError(f"Output must not be a symbolic link: {target}")
        for source in inputs:
            if target == source or (target.exists() and target.samefile(source)):
                raise EbookBuildError(f"Output would overwrite input: {target}")
        if target.exists() and (not overwrite or not target.is_file()):
            raise EbookBuildError(
                f"Output exists (use --overwrite for files): {target}"
            )

    toc = ["# 목차\n\n", f"{_markdown_text(title)}\n\n"]
    basic = [f"# {_markdown_text(title)}\n\n", "## 목차\n\n"]
    for index, (chapter_title, _, _) in enumerate(chapters, start=1):
        label = _markdown_text(chapter_title)
        anchor = f"chapter-{index:03d}"
        toc.append(f"{index}. [{label}](basic.md#{anchor})\n")
        basic.append(f"{index}. [{label}](#{anchor})\n")
    for index, (chapter_title, _, body) in enumerate(chapters, start=1):
        basic.append(
            f'\n<a id="chapter-{index:03d}"></a>\n\n'
            f"## {index}. {_markdown_text(chapter_title)}\n\n{body}"
        )
        basic.append("\n" if body.endswith("\n") else "\n\n")

    output_dir.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is the default: a competing process cannot silently overwrite.
    mode = "w" if overwrite else "x"
    with outputs[0].open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write("".join(toc))
    with outputs[1].open(mode, encoding="utf-8", newline="\n") as stream:
        stream.write("".join(basic))
    LOGGER.info("Built %d chapters in %s", len(chapters), output_dir)
    return BuildResult(outputs[0], outputs[1], len(chapters))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build_ebook(args.manifest, args.output_dir, overwrite=args.overwrite)
    except (EbookBuildError, OSError, UnicodeError, RuntimeError) as exc:
        print(f"Ebook build failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Created {result.chapter_count} chapters: {result.toc_path}, {result.basic_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
