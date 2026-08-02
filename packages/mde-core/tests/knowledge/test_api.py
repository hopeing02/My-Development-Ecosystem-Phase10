from pathlib import Path
from urllib.parse import quote

from fastapi.testclient import TestClient

from mde.knowledge.api import create_app
from mde.knowledge.service import KnowledgeService


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_graph_api_is_source_scoped_read_only_and_hides_paths(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    docs = tmp_path / "docs"
    personal = tmp_path / "personal"
    _write(docs / "A.md", "---\ntags: [architecture]\n---\n# A\n[[folder/B]]")
    _write(docs / "folder" / "B.md", "# B\npublic preview")
    _write(personal / "Private.md", "# Private\nsecret needle")
    docs_source = knowledge_service.add_source(
        docs, name="docs", category="development"
    )
    private_source = knowledge_service.add_source(
        personal, name="personal", category="personal", source_type="obsidian"
    )
    knowledge_service.scan_source(docs_source.id)
    knowledge_service.scan_source(private_source.id)
    client = TestClient(create_app(knowledge_service))

    sources_response = client.get("/api/v1/knowledge/sources")
    assert sources_response.status_code == 200
    sources = sources_response.json()["data"]["sources"]
    assert {source["id"] for source in sources} == {"ks-001", "ks-002"}
    assert all("path" not in source for source in sources)

    graph_response = client.get(f"/api/v1/knowledge/sources/{docs_source.id}/graph")
    assert graph_response.status_code == 200
    graph = graph_response.json()["data"]
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source"].endswith("::A.md")
    assert graph["edges"][0]["target"].endswith("::folder/B.md")

    private_denied = client.get(f"/api/v1/knowledge/sources/{private_source.id}/graph")
    assert private_denied.status_code == 403
    assert private_denied.json()["error"]["code"] == "SENSITIVE_SOURCE_NOT_ALLOWED"
    private_allowed = client.get(
        f"/api/v1/knowledge/sources/{private_source.id}/graph",
        params={"confirmSensitive": "true"},
    )
    assert private_allowed.status_code == 200

    default_search = client.get(
        "/api/v1/knowledge/search", params={"q": "secret needle"}
    )
    assert default_search.json()["data"]["documents"] == []


def test_graph_api_document_detail_search_tags_and_validation(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    docs = tmp_path / "docs"
    _write(
        docs / "A.md",
        "---\naliases: [Alpha]\ntags: [architecture]\n---\n# A\n[[folder/B]]\n[[Missing]]",
    )
    _write(docs / "folder" / "B.md", "# B\n" + "preview " * 400)
    source = knowledge_service.add_source(docs, name="docs", category="development")
    knowledge_service.scan_source(source.id)
    client = TestClient(create_app(knowledge_service))
    document_id = f"{source.id}::folder/B.md"
    encoded = quote(document_id, safe="")

    detail_response = client.get(
        f"/api/v1/knowledge/sources/{source.id}/documents/{encoded}"
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]["document"]
    assert detail["title"] == "B"
    assert len(detail["preview"]) == 2000
    assert detail["incomingLinks"] == [
        {"documentId": f"{source.id}::A.md", "sourceId": source.id, "title": "A"}
    ]
    assert detail["indexedAt"]

    graph_response = client.get(
        f"/api/v1/knowledge/sources/{source.id}/documents/{encoded}/graph",
        params={"depth": 1, "direction": "incoming", "includeBroken": "true"},
    )
    assert graph_response.status_code == 200
    assert {node["title"] for node in graph_response.json()["data"]["nodes"]} == {
        "A",
        "B",
    }

    tags = client.get(f"/api/v1/knowledge/sources/{source.id}/tags")
    assert tags.json()["data"]["tags"] == [{"name": "architecture", "documentCount": 1}]
    search = client.get(
        "/api/v1/knowledge/search",
        params={"q": "Alpha", "sourceId": source.id, "tag": "architecture"},
    )
    assert [item["title"] for item in search.json()["data"]["documents"]] == ["A"]

    invalid = client.get(
        f"/api/v1/knowledge/sources/{source.id}/documents/{encoded}/graph",
        params={"depth": 4},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_DEPTH"

    invalid_query = client.get("/api/v1/knowledge/search")
    assert invalid_query.status_code == 400
    assert invalid_query.json()["error"]["code"] == "INVALID_QUERY"


def test_graph_api_serves_built_viewer_assets(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    viewer = tmp_path / "dist"
    assets = viewer / "assets"
    icons = viewer / "icons"
    assets.mkdir(parents=True)
    icons.mkdir()
    (viewer / "index.html").write_text(
        '<div id="root">viewer</div><script src="/assets/app.js"></script>',
        encoding="utf-8",
    )
    (assets / "app.js").write_text("console.log('viewer')", encoding="utf-8")
    (viewer / "manifest.webmanifest").write_text(
        '{"name":"MDE Knowledge Viewer"}', encoding="utf-8"
    )
    (viewer / "sw.js").write_text("self.skipWaiting()", encoding="utf-8")
    (icons / "viewer.svg").write_text("<svg></svg>", encoding="utf-8")
    client = TestClient(create_app(knowledge_service, viewer_dist=viewer))

    assert client.get("/").text.startswith('<div id="root">viewer</div>')
    assert client.get("/assets/app.js").text == "console.log('viewer')"
    assert client.get("/manifest.webmanifest").headers["content-type"].startswith(
        "application/manifest+json"
    )
    service_worker = client.get("/sw.js")
    assert service_worker.text == "self.skipWaiting()"
    assert service_worker.headers["service-worker-allowed"] == "/"
    assert client.get("/icons/viewer.svg").text == "<svg></svg>"


def test_graph_api_disables_api_response_caching(
    knowledge_service: KnowledgeService,
) -> None:
    client = TestClient(create_app(knowledge_service))

    response = client.get("/api/v1/knowledge/sources")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_android_apk_download_serves_only_configured_file(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    apk = tmp_path / "viewer.apk"
    apk.write_bytes(b"safe-apk")
    client = TestClient(create_app(knowledge_service, android_apk_path=apk))

    response = client.get("/downloads/mde-knowledge-viewer.apk")

    assert response.status_code == 200
    assert response.content == b"safe-apk"
    assert response.headers["content-type"] == "application/vnd.android.package-archive"
    assert "mde-knowledge-viewer-v0.1.0.apk" in response.headers[
        "content-disposition"
    ]
    assert response.headers["cache-control"] == "no-store"


def test_android_apk_download_returns_not_found_when_build_is_missing(
    tmp_path: Path, knowledge_service: KnowledgeService
) -> None:
    client = TestClient(
        create_app(knowledge_service, android_apk_path=tmp_path / "missing.apk")
    )

    response = client.get("/downloads/mde-knowledge-viewer.apk")

    assert response.status_code == 404
    assert response.json() == {"detail": "Android APK is not available."}
