"""Safe Markdown capture with optional MDE single-file indexing."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from autoknowledge_lite.mde_client import MDEClientError, MDEKnowledgeClient

INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
SEPARATORS = re.compile(r"[\s-]+")
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
MDE_UNAVAILABLE = {
    "MDE_NOT_FOUND",
    "MDE_TIMEOUT",
    "MDE_EXECUTION_ERROR",
    "INVALID_RESPONSE",
    "UNSUPPORTED_API_VERSION",
}


@dataclass(frozen=True)
class CaptureSaveResult:
    file_saved: bool
    saved_path: Path | None
    relative_path: str | None
    index_attempted: bool
    index_succeeded: bool
    document_id: str | None
    warnings: tuple[str, ...]
    error_code: str | None


@dataclass(frozen=True)
class IndexFailure:
    source_name: str
    relative_path: str
    saved_at: str
    index_status: str
    error_code: str


class IndexFailureStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _data_dir() / "index-failures.json"

    def list(self) -> tuple[IndexFailure, ...]:
        if not self.path.exists():
            return ()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return tuple(IndexFailure(**item) for item in payload)
        except (OSError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("Unable to read index failure records.") from error

    def add(self, failure: IndexFailure) -> None:
        records = [*self.list(), failure]
        self._save(records)

    def remove(self, source_name: str, relative_path: str) -> None:
        self._save(
            [
                record
                for record in self.list()
                if not (
                    record.source_name == source_name
                    and record.relative_path == relative_path
                )
            ]
        )

    def _save(self, records: list[IndexFailure]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([asdict(item) for item in records], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


class CaptureService:
    def __init__(
        self,
        mde_client: MDEKnowledgeClient | None = None,
        failure_store: IndexFailureStore | None = None,
        fallback_vault: Path | None = None,
    ) -> None:
        self.mde_client = mde_client or MDEKnowledgeClient()
        self.failure_store = failure_store or IndexFailureStore()
        self.fallback_vault = (
            fallback_vault or Path(os.getenv("AUTOKNOWLEDGE_VAULT_DIR", "vault"))
        ).resolve()

    def save(
        self,
        *,
        title: str,
        content: str,
        tags: tuple[str, ...] = (),
        source_name: str | None = None,
        folder: str = "00_Inbox",
    ) -> CaptureSaveResult:
        clean_title = " ".join(title.split())
        if not clean_title or not content.strip():
            return CaptureSaveResult(
                False, None, None, False, False, None, (), "INVALID_ARGUMENT"
            )

        index_source: str | None = None
        warnings: list[str] = []
        root = self.fallback_vault
        if source_name:
            try:
                source = self.mde_client.source_path(source_name)
                if not source.writable_by_capture_app or source.path is None:
                    raise MDEClientError(
                        "SOURCE_NOT_WRITABLE", "Source is not writable by capture apps."
                    )
                root = source.path.resolve(strict=True)
                index_source = source.name
            except MDEClientError as error:
                if error.code not in MDE_UNAVAILABLE:
                    return CaptureSaveResult(
                        False, None, None, False, False, None, (), error.code
                    )
                warnings.append("MDE를 사용할 수 없어 기존 Vault에 저장했습니다.")

        try:
            destination_directory = _safe_directory(root, folder)
            destination_directory.mkdir(parents=True, exist_ok=True)
            destination = _available_path(
                destination_directory, safe_filename(clean_title)
            )
            markdown = render_capture_markdown(clean_title, content, tags)
            temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
            temporary.write_text(markdown, encoding="utf-8")
            temporary.rename(destination)
        except (OSError, ValueError):
            return CaptureSaveResult(
                False,
                None,
                None,
                False,
                False,
                None,
                tuple(warnings),
                "FILE_SAVE_ERROR",
            )

        relative_path = destination.relative_to(root).as_posix()
        if index_source is None:
            return CaptureSaveResult(
                True,
                destination,
                relative_path,
                False,
                False,
                None,
                tuple(warnings),
                None,
            )
        try:
            indexed = self.mde_client.index_file(index_source, relative_path)
        except MDEClientError as error:
            self.failure_store.add(
                IndexFailure(
                    source_name=index_source,
                    relative_path=relative_path,
                    saved_at=datetime.now(timezone.utc).isoformat(),
                    index_status="failed",
                    error_code=error.code,
                )
            )
            warnings.append("문서는 저장됐지만 Knowledge 색인에 실패했습니다.")
            return CaptureSaveResult(
                True,
                destination,
                relative_path,
                True,
                False,
                None,
                tuple(warnings),
                error.code,
            )
        return CaptureSaveResult(
            True,
            destination,
            relative_path,
            True,
            True,
            str(indexed.get("documentId")) if indexed.get("documentId") else None,
            tuple(warnings),
            None,
        )

    def retry_index(self, source_name: str, relative_path: str) -> dict[str, object]:
        result = self.mde_client.index_file(source_name, relative_path)
        self.failure_store.remove(source_name, relative_path)
        return result


def safe_filename(title: str, *, maximum: int = 100) -> str:
    stem = INVALID_FILENAME.sub("-", title)
    stem = SEPARATORS.sub("-", stem).strip(" .-")[:maximum].rstrip(" .-")
    if not stem:
        stem = "untitled"
    if stem.upper() in WINDOWS_RESERVED:
        stem = f"_{stem}"
    return f"{stem}.md"


def render_capture_markdown(title: str, content: str, tags: tuple[str, ...]) -> str:
    created = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"created: {created}",
        "source_type: clipboard",
    ]
    clean_tags = tuple(
        dict.fromkeys(tag.strip().lstrip("#") for tag in tags if tag.strip())
    )
    if clean_tags:
        lines.append("tags:")
        lines.extend(f"  - {json.dumps(tag, ensure_ascii=False)}" for tag in clean_tags)
    else:
        lines.append("tags: []")
    lines.extend(("---", "", f"# {title}", "", content.strip(), ""))
    return "\n".join(lines)


def _safe_directory(root: Path, folder: str) -> Path:
    relative = Path(folder)
    if relative.is_absolute():
        raise ValueError("Folder must be source-relative.")
    destination = (root / relative).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError("Folder is outside the source.") from error
    return destination


def _available_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    for number in range(2, 10000):
        alternative = directory / f"{stem}-{number}.md"
        if not alternative.exists():
            return alternative
    raise OSError("Unable to allocate a unique Markdown filename.")


def _data_dir() -> Path:
    configured = os.getenv("AUTOKNOWLEDGE_DATA_DIR")
    return Path(configured).resolve() if configured else Path("data").resolve()
