"""Markdown rendering for analyzed knowledge records."""

from __future__ import annotations

from autoknowledge_lite.knowledge_graph import (
    metadata_for_record,
    render_connections,
    render_note,
)

from autoknowledge_lite.models import ShareRecord


class MarkdownRenderError(RuntimeError):
    """Raised when a share record is not ready for Markdown rendering."""


def render_markdown(record: ShareRecord) -> str:
    """Render a validated analysis as Markdown with YAML-compatible metadata."""

    if record.analysis is None:
        raise MarkdownRenderError("Share job has not been analyzed.")

    title = record.title or record.analysis.summary[:80] or "Untitled knowledge"
    source = record.source_url or ""
    metadata = metadata_for_record(record)
    points = "\n".join(f"- {point}" for point in record.analysis.key_points)
    properties: dict[str, object] = {
        "title": title,
        "aliases": list(metadata.aliases),
        "source_url": source,
        "received_at": record.received_at.isoformat(),
        "tags": list(metadata.tags),
        "type": metadata.note_type,
        "status": metadata.status,
        "reviewed": metadata.reviewed,
        "topics": [f"[[{topic}]]" for topic in metadata.topics],
    }
    if record.source_type:
        properties.update(
            {
                "source_type": record.source_type,
                "source_app": record.source_app or "",
                "capture_type": "clipboard_item",
                "capture_device": "android",
                "capture_method": "android_clipboard",
                "captured_at": (record.captured_at or record.received_at).isoformat(),
                "content_hash": record.content_hash or "",
                "parent_document": record.parent_document_id,
            }
        )
    body = (
        f"# {title}\n\n"
        "## Summary\n\n"
        f"{record.analysis.summary}\n\n"
        "## Key Points\n\n"
        f"{points}\n\n"
        "## Original Content\n\n"
        f"{record.content.rstrip()}\n\n"
        f"{render_connections(metadata)}"
    )
    return render_note(properties, body)
