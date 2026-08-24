"""Versioned JSON CLI client for the MDE Knowledge Plugin."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

SUPPORTED_API_VERSION = "1"


class MDEClientError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CaptureSource:
    id: str
    name: str
    category: str
    source_type: str
    enabled: bool
    sensitive: bool
    writable_by_capture_app: bool
    path: Path | None = None


@dataclass(frozen=True)
class KnowledgeDocumentCandidate:
    id: str
    source_id: str
    title: str
    relative_path: str
    snippet: str


Runner = Callable[..., subprocess.CompletedProcess[str]]


class MDEKnowledgeClient:
    """Invoke only the public MDE JSON CLI contract."""

    def __init__(
        self,
        command: list[str] | tuple[str, ...] | None = None,
        *,
        timeout: float = 30,
        runner: Runner = subprocess.run,
    ) -> None:
        self.command = tuple(command or command_from_environment())
        self.timeout = timeout
        self.runner = runner

    def integration_info(self) -> dict[str, Any]:
        return self._invoke("integration-info")

    def list_sources(self) -> tuple[CaptureSource, ...]:
        payload = self._invoke("list")
        return tuple(self._source(item) for item in payload.get("sources", ()))

    def source_path(self, source: str) -> CaptureSource:
        payload = self._invoke("source-path", source)
        item = payload.get("source")
        if not isinstance(item, dict):
            raise MDEClientError("INVALID_RESPONSE", "MDE source response is invalid.")
        parsed = self._source(item)
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise MDEClientError("INVALID_RESPONSE", "MDE source path is missing.")
        return CaptureSource(**{**parsed.__dict__, "path": Path(path)})

    def index_file(self, source: str, relative_path: str) -> dict[str, Any]:
        payload = self._invoke(
            "index-file", "--source", source, "--path", relative_path
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise MDEClientError("INVALID_RESPONSE", "MDE index response is invalid.")
        return result

    def search_documents(
        self, source: str, query: str, *, limit: int = 20
    ) -> tuple[KnowledgeDocumentCandidate, ...]:
        payload = self._invoke(
            "search",
            query,
            "--source",
            source,
            "--include-sensitive",
            "--limit",
            str(limit),
        )
        documents = payload.get("documents")
        if not isinstance(documents, list):
            raise MDEClientError("INVALID_RESPONSE", "MDE search response is invalid.")
        result: list[KnowledgeDocumentCandidate] = []
        for item in documents:
            if not isinstance(item, dict):
                raise MDEClientError(
                    "INVALID_RESPONSE", "MDE search document is invalid."
                )
            try:
                result.append(
                    KnowledgeDocumentCandidate(
                        id=str(item["id"]),
                        source_id=str(item["sourceId"]),
                        title=str(item["title"]),
                        relative_path=str(item["relativePath"]),
                        snippet=str(item.get("snippet", "")),
                    )
                )
            except KeyError as error:
                raise MDEClientError(
                    "INVALID_RESPONSE", "MDE search document is incomplete."
                ) from error
        return tuple(result)

    def link_child(
        self,
        source: str,
        parent_document_id: str,
        target_document_id: str,
    ) -> dict[str, Any]:
        payload = self._invoke(
            "link-child",
            "--source",
            source,
            "--parent",
            parent_document_id,
            "--target",
            target_document_id,
            "--confirm-sensitive",
        )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise MDEClientError(
                "INVALID_RESPONSE", "MDE parent-link response is invalid."
            )
        return result

    def _invoke(self, action: str, *arguments: str) -> dict[str, Any]:
        command = [
            *self.command,
            "knowledge",
            action,
            *arguments,
            "--format",
            "json",
        ]
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=self.timeout,
                check=False,
                shell=False,
            )
        except FileNotFoundError as error:
            raise MDEClientError(
                "MDE_NOT_FOUND", "MDE command was not found."
            ) from error
        except subprocess.TimeoutExpired as error:
            raise MDEClientError("MDE_TIMEOUT", "MDE command timed out.") from error
        except (OSError, subprocess.SubprocessError) as error:
            raise MDEClientError("MDE_EXECUTION_ERROR", "Unable to run MDE.") from error
        stdout = completed.stdout
        if not isinstance(stdout, (str, bytes, bytearray)) or not stdout.strip():
            raise MDEClientError(
                "INVALID_RESPONSE", "MDE did not return valid JSON."
            )
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as error:
            raise MDEClientError(
                "INVALID_RESPONSE", "MDE did not return valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise MDEClientError("INVALID_RESPONSE", "MDE response is invalid.")
        if payload.get("apiVersion") != SUPPORTED_API_VERSION:
            raise MDEClientError(
                "UNSUPPORTED_API_VERSION", "MDE integration version is not supported."
            )
        if completed.returncode != 0 or payload.get("success") is not True:
            error = payload.get("error")
            code = (
                str(error.get("code", "MDE_ERROR"))
                if isinstance(error, dict)
                else "MDE_ERROR"
            )
            message = (
                str(error.get("message", "MDE command failed."))
                if isinstance(error, dict)
                else "MDE command failed."
            )
            raise MDEClientError(code, message)
        return payload

    @staticmethod
    def _source(item: object) -> CaptureSource:
        if not isinstance(item, dict):
            raise MDEClientError("INVALID_RESPONSE", "MDE source response is invalid.")
        try:
            return CaptureSource(
                id=str(item["id"]),
                name=str(item["name"]),
                category=str(item["category"]),
                source_type=str(item["sourceType"]),
                enabled=bool(item["enabled"]),
                sensitive=bool(item["sensitive"]),
                writable_by_capture_app=bool(item["writableByCaptureApp"]),
            )
        except KeyError as error:
            raise MDEClientError(
                "INVALID_RESPONSE", "MDE source response is incomplete."
            ) from error


def command_from_environment() -> list[str]:
    configured = os.getenv("AUTOKNOWLEDGE_MDE_COMMAND")
    if configured:
        try:
            command = json.loads(configured)
        except json.JSONDecodeError as error:
            raise MDEClientError(
                "INVALID_CONFIGURATION",
                "AUTOKNOWLEDGE_MDE_COMMAND must be a JSON array.",
            ) from error
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(item, str) and item for item in command)
        ):
            raise MDEClientError(
                "INVALID_CONFIGURATION",
                "AUTOKNOWLEDGE_MDE_COMMAND must be a non-empty JSON string array.",
            )
        return command
    executable_name = "mde.exe" if os.name == "nt" else "mde"
    scripts_directory = "Scripts" if os.name == "nt" else "bin"
    monorepo_executable = (
        Path(__file__).resolve().parents[4]
        / ".venv"
        / scripts_directory
        / executable_name
    )
    if monorepo_executable.is_file():
        return [str(monorepo_executable)]
    executable = shutil.which("mde") or shutil.which("mde.exe")
    if executable:
        return [executable]
    return ["mde"]
