from __future__ import annotations

import json
from datetime import datetime, timezone

from autoknowledge_lite.content import extract_web_content, should_fetch_content
from autoknowledge_lite.models import ShareRecord


def test_chatgpt_share_extracts_embedded_conversation_text() -> None:
    message = "# Answer\n\n" + "Useful explanation. " * 20
    system_prompt = "You are an internal system.\n" + "Do not select this. " * 100
    developer_prompt = (
        "First-response output contract — follow this exact shape:\n"
        + "Internal instruction. " * 100
    )
    loader_data = json.dumps(
        {
            "mapping": message,
            "system": system_prompt,
            "developer": developer_prompt,
            "indexes": list(range(100)),
        }
    )
    html = f"<html><script>window.data=[{json.dumps(loader_data)}]</script></html>"

    extracted = extract_web_content("https://chatgpt.com/share/example", html)

    assert extracted == message.strip()


def test_generic_page_extracts_visible_text_only() -> None:
    html = "<html><body><h1>Title</h1><script>secret()</script><p>Article</p></body></html>"

    extracted = extract_web_content("https://example.com/article", html)

    assert extracted == "Title\nArticle"


def test_url_only_share_requires_fetching() -> None:
    record = ShareRecord(
        job_id="00000000-0000-0000-0000-000000000001",
        received_at=datetime.now(timezone.utc),
        content="https://example.com/article",
        source_url="https://example.com/article",
    )

    assert should_fetch_content(record) is True
