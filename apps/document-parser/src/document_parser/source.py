"""Validate local document paths without opening or modifying their contents."""

from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from stat import S_ISREG
from typing import Literal

DocumentFormat = Literal["hwp", "hwpx", "pdf"]
_FORMATS: dict[str, DocumentFormat] = {
    ".hwp": "hwp",
    ".hwpx": "hwpx",
    ".pdf": "pdf",
}


@dataclass(frozen=True, slots=True)
class DocumentSource:
    """Validated path and extension-based format; no content validity guarantee."""

    path: Path
    format: DocumentFormat


def validate_source(path: str | PathLike[str]) -> DocumentSource:
    """Check a local regular file, then its case-insensitive final suffix.

    Return its un-resolved Path and lowercase format without a leading dot.
    Raise ValueError for empty paths, non-regular files or unsupported suffixes;
    TypeError for invalid path types. Filesystem errors propagate unchanged,
    including FileNotFoundError and PermissionError. Symlinks are followed.
    """
    if isinstance(path, str) and not path:
        raise ValueError("Source path must not be empty")
    source_path = Path(path)
    if not S_ISREG(source_path.stat().st_mode):
        raise ValueError("Source must be a regular file")
    document_format = _FORMATS.get(source_path.suffix.lower())
    if document_format is None:
        raise ValueError("Supported source extensions are .hwp, .hwpx and .pdf")
    return DocumentSource(path=source_path, format=document_format)


def inspect_document_source(file_path: str | Path) -> DocumentSource:
    """Expose the original STEP API while reusing verified source validation."""
    return validate_source(Path(file_path).expanduser())
