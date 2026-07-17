from __future__ import annotations

import json
from typing import Any

from mde.ai.errors import AIResponseValidationError
from mde.ai.models import AIArtifact


def extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as error:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise AIResponseValidationError(
                "AI response does not contain valid JSON."
            ) from error
        try:
            value = json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as nested:
            raise AIResponseValidationError(
                "AI response JSON could not be parsed."
            ) from nested
    if not isinstance(value, dict):
        raise AIResponseValidationError("AI response JSON must be an object.")
    return value


def parse_artifact_document(
    document: dict[str, Any],
) -> tuple[str, tuple[AIArtifact, ...]]:
    summary = document.get("summary", "")
    if not isinstance(summary, str) or not summary.strip():
        raise AIResponseValidationError("AI response requires a non-empty summary.")
    raw_artifacts = document.get("artifacts", [])
    if not isinstance(raw_artifacts, list):
        raise AIResponseValidationError("AI response artifacts must be a list.")
    artifacts: list[AIArtifact] = []
    for index, item in enumerate(raw_artifacts):
        if not isinstance(item, dict):
            raise AIResponseValidationError(f"Artifact {index} must be an object.")
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            raise AIResponseValidationError(f"Artifact {index} requires path.")
        if not isinstance(content, str):
            raise AIResponseValidationError(
                f"Artifact {index} requires string content."
            )
        media_type = item.get("media_type", "text/plain")
        artifacts.append(
            AIArtifact(path=path, content=content, media_type=str(media_type))
        )
    return summary.strip(), tuple(artifacts)
