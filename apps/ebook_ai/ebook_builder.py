"""Assemble a reviewed Markdown manuscript list into a table of contents and book."""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

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


def _read_supplements(
    supplements_path: Path,
    manifest_path: Path,
    chapters: list[tuple[str, Path, str]],
) -> dict[str, tuple[Path, str]]:
    """Read only explicitly listed supplements within the manuscript input root."""
    try:
        document = json.loads(supplements_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EbookBuildError(
            f"Cannot read supplements JSON: {supplements_path}: {exc}"
        ) from exc
    entries = document.get("supplements") if isinstance(document, dict) else None
    if not isinstance(entries, list) or not entries:
        raise EbookBuildError("supplements: non-empty list required")
    root = manifest_path.parent
    valid_steps = {f"chapter-{index:03d}" for index in range(1, len(chapters) + 1)}
    protected = [manifest_path, supplements_path, *(path for _, path, _ in chapters)]
    supplements: dict[str, tuple[Path, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise EbookBuildError("Each supplement must be an object")
        step = _title(entry.get("step"), "supplement.step")
        if step not in valid_steps:
            raise EbookBuildError(f"Unknown supplement step (use chapter-NNN): {step}")
        if step in supplements:
            raise EbookBuildError(f"Duplicate supplement step: {step}")
        value = entry.get("path")
        if not isinstance(value, str) or not value.strip() or "\0" in value:
            raise EbookBuildError("supplement.path: non-empty relative path required")
        relative = PureWindowsPath(value)
        if relative.drive or relative.root or ".." in relative.parts or ":" in value:
            raise EbookBuildError(f"Unsafe supplement path: {value}")
        source = (root / Path(*relative.parts)).resolve()
        if not source.is_relative_to(root):
            raise EbookBuildError(f"Supplement path escapes input root: {value}")
        if source.suffix.lower() != ".md":
            raise EbookBuildError(f"Markdown (.md) supplement required: {value}")
        try:
            body = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise EbookBuildError(f"Cannot read supplement: {source}: {exc}") from exc
        if not body.strip():
            raise EbookBuildError(f"Empty supplement: {source}")
        if any(source.samefile(path) for path in protected):
            raise EbookBuildError(f"Duplicate supplement/input file: {source}")
        protected.append(source)
        supplements[step] = (source, body)
    return supplements


def build_ebook(
    manifest_path: str | Path,
    output_dir: str | Path,
    *,
    overwrite: bool = False,
    supplements_path: str | Path | None = None,
) -> BuildResult:
    """Build toc.md/basic.md in manifest order after validating every manuscript.

    Paths in the manifest are relative to that manifest, never the working directory.
    Body text is preserved, except UTF-8 BOM removal and newline normalization to LF.
    Manuscript review/approval is the caller's responsibility.
    With supplements_path, matching existing base outputs are kept and expanded.md
    is added. In this mode overwrite applies only to expanded.md.
    """
    manifest_path = Path(manifest_path).resolve()
    title, chapters = _read_manifest(manifest_path)
    supplements = {}
    if supplements_path is not None:
        supplements_path = Path(supplements_path).resolve()
        supplements = _read_supplements(supplements_path, manifest_path, chapters)
    output_dir = Path(output_dir).resolve()
    outputs = (output_dir / "toc.md", output_dir / "basic.md")
    expanded_path = output_dir / "expanded.md"
    if all(target.exists() for target in outputs) and outputs[0].samefile(outputs[1]):
        raise EbookBuildError("Output files must be distinct files")
    inputs = [manifest_path, *(source for _, source, _ in chapters)]
    if supplements_path is not None:
        inputs.extend(
            [supplements_path, *(source for source, _ in supplements.values())]
        )
    for target in (
        (*outputs, expanded_path) if supplements_path is not None else outputs
    ):
        if target.is_symlink():
            raise EbookBuildError(f"Output must not be a symbolic link: {target}")
        for source in inputs:
            if target == source or (target.exists() and target.samefile(source)):
                raise EbookBuildError(f"Output would overwrite input: {target}")
        if target.exists() and (
            not target.is_file()
            or (not overwrite and (supplements_path is None or target == expanded_path))
        ):
            raise EbookBuildError(
                f"Output exists (use --overwrite for files): {target}"
            )
        if (
            supplements_path is not None
            and expanded_path.exists()
            and target in outputs
        ):
            if target.exists() and target.samefile(expanded_path):
                raise EbookBuildError("Output files must be distinct files")

    toc = ["# 목차\n\n", f"{_markdown_text(title)}\n\n"]
    basic = [f"# {_markdown_text(title)}\n\n", "## 목차\n\n"]
    for index, (chapter_title, _, _) in enumerate(chapters, start=1):
        label = _markdown_text(chapter_title)
        anchor = f"chapter-{index:03d}"
        toc.append(f"{index}. [{label}](basic.md#{anchor})\n")
        basic.append(f"{index}. [{label}](#{anchor})\n")
    expanded = basic.copy() if supplements else []
    for index, (chapter_title, _, body) in enumerate(chapters, start=1):
        chapter_start = len(basic)
        basic.append(
            f'\n<a id="chapter-{index:03d}"></a>\n\n'
            f"## {index}. {_markdown_text(chapter_title)}\n\n{body}"
        )
        basic.append("\n" if body.endswith("\n") else "\n\n")
        if supplements:
            expanded.extend(basic[chapter_start:])
        if f"chapter-{index:03d}" in supplements:
            supplement_body = supplements[f"chapter-{index:03d}"][1]
            expanded.append(f"### 추가 해설\n\n{supplement_body}")
            expanded.append("\n" if supplement_body.endswith("\n") else "\n\n")

    texts = ("".join(toc), "".join(basic))
    if supplements_path is not None:
        for target, text in zip(outputs, texts):
            if target.exists() and target.read_bytes() != text.encode("utf-8"):
                raise EbookBuildError(
                    f"Existing STEP 01 output differs; preserved: {target}"
                )

    output_dir.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is the default: a competing process cannot silently overwrite.
    mode = "w" if overwrite else "x"
    for target, text in zip(outputs, texts):
        if supplements_path is not None and target.exists():
            continue
        with target.open(
            mode if supplements_path is None else "x", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(text)
    if supplements_path is not None:
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=output_dir,
                prefix=".expanded-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = Path(stream.name)
                stream.write("".join(expanded))
            if overwrite:
                os.replace(temporary_path, expanded_path)
            else:
                # Publish a complete file without overwriting a concurrently created target.
                os.link(temporary_path, expanded_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
    LOGGER.info("Built %d chapters in %s", len(chapters), output_dir)
    return BuildResult(outputs[0], outputs[1], len(chapters))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--supplements",
        type=Path,
        help="Approved supplements JSON; creates expanded.md",
    )
    args = parser.parse_args(argv)
    try:
        result = build_ebook(
            args.manifest,
            args.output_dir,
            overwrite=args.overwrite,
            supplements_path=args.supplements,
        )
    except (EbookBuildError, OSError, UnicodeError, RuntimeError) as exc:
        print(f"Ebook build failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"Created {result.chapter_count} chapters: {result.toc_path}, {result.basic_path}"
    )
    if args.supplements is not None:
        print(f"Expanded edition: {result.basic_path.parent / 'expanded.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
