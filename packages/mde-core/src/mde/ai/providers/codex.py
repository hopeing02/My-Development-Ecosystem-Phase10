"""Adapt an authenticated Codex CLI to MDE's artifact response contract."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import psutil

from mde.ai.errors import (
    AIConfigurationError,
    AIResponseValidationError,
    AITransportError,
)
from mde.ai.models import AIRequest, AIResponse
from mde.ai.parsing import extract_json_object, parse_artifact_document
from mde.ai.providers.base_http import BaseHTTPAIProvider, SYSTEM_PROMPT


class CodexCLIProvider:
    """Return proposed files; MDE retains responsibility for applying and testing."""

    name = "codex"

    def execute(self, request: AIRequest) -> AIResponse:
        executable = shutil.which(os.getenv("MDE_CODEX_EXECUTABLE", "codex"))
        if not executable:
            raise AIConfigurationError("Codex CLI not found. Set MDE_CODEX_EXECUTABLE.")
        try:
            timeout = float(os.getenv("MDE_CODEX_TIMEOUT", "180"))
            if not math.isfinite(timeout) or not 0 < timeout <= 1800:
                raise ValueError
        except ValueError as error:
            raise AIConfigurationError(
                "MDE_CODEX_TIMEOUT must be in (0, 1800]."
            ) from error
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["summary", "artifacts", "approved"],
            "properties": {
                "summary": {"type": "string"},
                "approved": {"type": "boolean"},
                "artifacts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["path", "content", "media_type"],
                        "properties": {
                            key: {"type": "string"}
                            for key in ("path", "content", "media_type")
                        },
                    },
                },
            },
        }
        with tempfile.TemporaryDirectory(prefix="mde-codex-") as temporary:
            directory = Path(temporary)
            schema_path = directory / "schema.json"
            output_path = directory / "response.json"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            command = [
                executable,
                "-a",
                "never",
                "exec",
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--color",
                "never",
                "--cd",
                str(request.repository_root.resolve()),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
            ]
            model = os.getenv("MDE_CODEX_MODEL", "").strip()
            if model:
                command.extend(["--model", model])
            command.append("-")
            prompt = (
                SYSTEM_PROMPT
                + "\nReturn full file contents as artifacts. Do not edit files, run commands, "
                "commit, push, or deploy. Use supplied context only. Do not delegate. "
                "For review, return artifacts=[] and judge the proposed contents. "
                "For other actions set approved=false; MDE runs review separately.\n"
                + BaseHTTPAIProvider.user_prompt(request)
            )
            try:
                process = subprocess.Popen(
                    command,
                    cwd=request.repository_root,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                try:
                    process.communicate(prompt, timeout=timeout)
                except subprocess.TimeoutExpired as error:
                    # The Windows CLI may have child processes; do not leave timed-out runs alive.
                    try:
                        owned = psutil.Process(process.pid)
                        children = owned.children(recursive=True)
                        for child in reversed(children):
                            try:
                                child.kill()
                            except psutil.NoSuchProcess:
                                pass
                    except psutil.Error:
                        pass
                    finally:
                        process.kill()
                        process.communicate()
                    raise AITransportError("Codex CLI timed out.") from error
            except OSError as error:
                raise AITransportError("Unable to start Codex CLI.") from error
            if process.returncode:
                # CLI diagnostics may contain prompts or credentials; never echo them.
                raise AITransportError(
                    f"Codex CLI exited with code {process.returncode}; check CLI login/configuration."
                )
            if not output_path.is_file():
                raise AIResponseValidationError("Codex CLI returned no response file.")
            document = extract_json_object(output_path.read_text(encoding="utf-8"))
            summary, artifacts = parse_artifact_document(document)
            if type(document.get("approved")) is not bool:
                raise AIResponseValidationError(
                    "Codex response requires boolean approved."
                )
            if request.action in {"generate", "fix"} and not artifacts:
                raise AIResponseValidationError("Codex returned no code artifacts.")
            if request.action == "review" and artifacts:
                raise AIResponseValidationError(
                    "Codex review must not replace artifacts."
                )
            return AIResponse(
                provider=self.name,
                action=request.action,
                summary=summary,
                artifacts=artifacts,
                metadata={
                    "approved": document["approved"],
                    "execution": "codex exec",
                    "model": model or "CLI configured default",
                },
            )
