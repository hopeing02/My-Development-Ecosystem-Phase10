from pathlib import Path

from fastapi.testclient import TestClient

from mde.knowledge.api import create_app
from mde.knowledge.service import KnowledgeService


def _client(tmp_path: Path) -> tuple[TestClient, Path, str]:
    vault = tmp_path / "vault"
    vault.mkdir()
    document = vault / "문서.md"
    document.write_text("---\ntitle: 원본\ncustom: 보존\n---\n# 원본\n본문\n", encoding="utf-8")
    service = KnowledgeService(registry_path=tmp_path / "sources.json", database_path=tmp_path / "knowledge.db")
    source = service.add_source(vault, name="개발", category="development")
    service.scan_source(source.id)
    return TestClient(create_app(service)), document, f"{source.id}::문서.md"


def test_command_api_previews_then_saves_document(tmp_path: Path) -> None:
    client, document, document_id = _client(tmp_path)
    detail = client.get(f"/api/v1/knowledge/sources/ks-001/documents/{document_id}").json()["data"]["document"]
    request = {
        "expectedContentHash": detail["contentHash"],
        "title": "변경",
        "tags": ["#MDE"],
        "aliases": ["별칭"],
        "body": "# 원본\n새 본문\n",
        "createBackup": True,
    }

    preview = client.post(
        f"/api/v1/knowledge/sources/ks-001/documents/{document_id}/preview-update",
        json=request,
    )
    assert preview.status_code == 200
    assert preview.json()["data"]["preview"]["after"]["title"] == "변경"
    assert "title: 원본" in document.read_text(encoding="utf-8")

    saved = client.patch(
        f"/api/v1/knowledge/sources/ks-001/documents/{document_id}",
        json=request,
    )
    assert saved.status_code == 200
    assert saved.json()["data"]["indexing"]["status"] == "completed"
    assert "title: 변경" in document.read_text(encoding="utf-8")


def test_command_api_rejects_conflict_non_json_and_remote_origin(tmp_path: Path) -> None:
    client, document, document_id = _client(tmp_path)
    detail = client.get(f"/api/v1/knowledge/sources/ks-001/documents/{document_id}").json()["data"]["document"]
    document.write_text("# 외부 변경\n", encoding="utf-8")
    payload = {
        "expectedContentHash": detail["contentHash"],
        "title": "충돌",
        "tags": [],
        "aliases": [],
        "body": "본문",
    }
    path = f"/api/v1/knowledge/sources/ks-001/documents/{document_id}"
    conflict = client.patch(path, json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "DOCUMENT_CONFLICT"

    non_json = client.patch(path, content="not-json", headers={"content-type": "text/plain"})
    assert non_json.status_code == 415
    remote = client.patch(path, json=payload, headers={"origin": "https://evil.example"})
    assert remote.status_code == 403
    assert remote.json()["error"]["code"] == "INVALID_ORIGIN"


def test_command_api_allows_same_origin_tailscale_host(tmp_path: Path) -> None:
    client, _, document_id = _client(tmp_path)
    client.base_url = "http://100.75.235.67"
    detail = client.get(
        f"/api/v1/knowledge/sources/ks-001/documents/{document_id}"
    ).json()["data"]["document"]
    response = client.post(
        f"/api/v1/knowledge/sources/ks-001/documents/{document_id}/preview-update",
        headers={"origin": "http://100.75.235.67"},
        json={
            "expectedContentHash": detail["contentHash"],
            "title": "Tailscale 편집",
            "tags": [],
            "aliases": [],
            "body": "본문",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["preview"]["after"]["title"] == "Tailscale 편집"


def test_command_api_rejects_public_host(tmp_path: Path) -> None:
    client, _, document_id = _client(tmp_path)
    client.base_url = "http://8.8.8.8"

    response = client.post(
        f"/api/v1/knowledge/sources/ks-001/documents/{document_id}/preview-update",
        json={},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INVALID_HOST"


def test_source_payload_exposes_viewer_edit_policy(tmp_path: Path) -> None:
    client, _, _ = _client(tmp_path)
    source = client.get("/api/v1/knowledge/sources").json()["data"]["sources"][0]
    assert source["readOnly"] is False
    assert source["editableInViewer"] is True
    assert source["allowLinkRewrite"] is True
