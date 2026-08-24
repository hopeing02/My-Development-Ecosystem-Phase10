"""Validated Markdown assembly and atomic source-file writes."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import yaml

from mde.knowledge.backup import KnowledgeBackupService
from mde.knowledge.errors import KnowledgeContractError
from mde.knowledge.parser import parse_markdown, split_frontmatter

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
_H1_LINE = re.compile(r"^(#\s+).+?$", re.MULTILINE)


def normalize_values(values: list[str], *, tags: bool = False) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if tags:
            cleaned = cleaned.lstrip("#").strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


class KnowledgeDocumentWriter:
    def __init__(self, backup: KnowledgeBackupService | None = None) -> None:
        self.backup = backup or KnowledgeBackupService()

    @staticmethod
    def resolve_path(source_root: Path, relative_path: str) -> Path:
        requested = Path(relative_path)
        if not relative_path.strip() or requested.is_absolute():
            raise KnowledgeContractError("PATH_OUTSIDE_SOURCE", "Document path must be source-relative.")
        root = source_root.resolve(strict=True)
        try:
            target = (root / requested).resolve(strict=True)
        except FileNotFoundError as error:
            raise KnowledgeContractError("DOCUMENT_NOT_FOUND", "Knowledge document was not found.") from error
        if not target.is_relative_to(root):
            raise KnowledgeContractError("PATH_OUTSIDE_SOURCE", "Document path is outside its source.")
        if target.suffix.casefold() != ".md" or not target.is_file():
            raise KnowledgeContractError("DOCUMENT_NOT_FOUND", "Knowledge document was not found.")
        return target

    @staticmethod
    def read(path: Path) -> tuple[bytes, str, bool]:
        data = path.read_bytes()
        if len(data) > MAX_DOCUMENT_BYTES:
            raise KnowledgeContractError("DOCUMENT_TOO_LARGE", "Document exceeds the 2 MB edit limit.")
        bom = data.startswith(b"\xef\xbb\xbf")
        try:
            text = data.decode("utf-8-sig" if bom else "utf-8")
        except UnicodeDecodeError as error:
            raise KnowledgeContractError("INVALID_MARKDOWN", "Document is not valid UTF-8 Markdown.") from error
        return data, text, bom

    @staticmethod
    def content_hash(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def assemble(
        self,
        current: str,
        *,
        title: str,
        tags: list[str],
        aliases: list[str],
        body: str,
    ) -> str:
        metadata, _, _, warnings = split_frontmatter(current)
        if warnings:
            raise KnowledgeContractError("INVALID_FRONTMATTER", "Existing frontmatter is invalid.")
        clean_title = title.strip()
        if not clean_title:
            raise KnowledgeContractError("INVALID_MARKDOWN", "Document title is required.")
        metadata["title"] = clean_title
        metadata["tags"] = normalize_values(tags, tags=True)
        metadata["aliases"] = normalize_values(aliases)
        next_body = body.replace("\r\n", "\n")
        if _H1_LINE.search(next_body):
            next_body = _H1_LINE.sub(lambda match: f"{match.group(1)}{clean_title}", next_body, count=1)
        frontmatter = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
        return f"---\n{frontmatter}\n---\n\n{next_body.lstrip()}"

    def write(
        self,
        path: Path,
        content: str,
        *,
        source_root: Path,
        relative_path: str,
        create_backup: bool,
        bom: bool,
    ) -> Path | None:
        encoded = content.encode("utf-8")
        if bom:
            encoded = b"\xef\xbb\xbf" + encoded
        if len(encoded) > MAX_DOCUMENT_BYTES:
            raise KnowledgeContractError("DOCUMENT_TOO_LARGE", "Document exceeds the 2 MB edit limit.")
        temporary = path.with_name(f"{path.name}.mde-tmp")
        backup_path: Path | None = None
        try:
            with temporary.open("wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            _, verify_text, _ = self.read(temporary)
            parsed = parse_markdown(verify_text, path)
            if parsed.warnings:
                raise KnowledgeContractError("INVALID_FRONTMATTER", "Generated frontmatter is invalid.")
            if create_backup:
                backup_path = self.backup.create(source_root, relative_path)
            os.replace(temporary, path)
        except KnowledgeContractError:
            if temporary.exists():
                temporary.unlink()
            raise
        except OSError as error:
            if temporary.exists():
                temporary.unlink()
            raise KnowledgeContractError("FILE_WRITE_ERROR", "Unable to write Markdown document.") from error
        return backup_path
