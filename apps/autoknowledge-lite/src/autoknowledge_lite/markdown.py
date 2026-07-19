"""Markdown rendering for analyzed knowledge records."""

from __future__ import annotations

import json

from autoknowledge_lite.models import ShareRecord


class MarkdownRenderError(RuntimeError):
    """Raised when a share record is not ready for Markdown rendering."""


def render_markdown(record: ShareRecord) -> str:
    """Render a validated analysis as Markdown with YAML-compatible metadata."""

    if record.analysis is None:
        raise MarkdownRenderError("Share job has not been analyzed.")

    title = record.title or record.analysis.summary[:80] or "Untitled knowledge"
    source = record.source_url or ""
    tags = "\n".join(f"  - {json.dumps(tag)}" for tag in record.analysis.tags)
    points = "\n".join(f"- {point}" for point in record.analysis.key_points)
    return (
        "---\n"
        f"title: {json.dumps(title)}\n"
        f"source_url: {json.dumps(source)}\n"
        f"received_at: {json.dumps(record.received_at.isoformat())}\n"
        "tags:\n"
        f"{tags}\n"
        "---\n\n"
        f"# {title}\n\n"
        f"{record.analysis.summary}\n\n"
        "## Key Points\n\n"
        f"{points}\n"
    )
