from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from autoknowledge_lite.api import create_app
from autoknowledge_lite.capture_api import normalize_capture_text
from autoknowledge_lite.capture_relations import (
    CaptureRelationMatcher,
    CaptureRelationRepository,
    CaptureRelationService,
    RelationStatus,
)
from autoknowledge_lite.cli import main as cli_main
from autoknowledge_lite.obsidian import ObsidianNoteStore
from autoknowledge_lite.store import JsonShareStore


class NullIndexer:
    def index_file(self, source: str, relative_path: str):
        return {"documentId": f"doc::{relative_path}"}

    def search_documents(self, source: str, query: str, *, limit: int = 20):
        return ()

    def link_child(self, source: str, parent_document_id: str, target_document_id: str):
        return {"fileSaved": True}


def digest(content: str) -> str:
    return hashlib.sha256(normalize_capture_text(content).encode("utf-8")).hexdigest()


def session(
    capture_id: str, content: str, *, message_id: str = "msg_1"
) -> dict[str, object]:
    payload = {
        "captureSessionId": capture_id,
        "sourceSessionId": f"source-{capture_id}",
        "clientType": "codex_app_server",
        "title": capture_id,
        "startedAt": "2026-08-03T12:00:00+09:00",
        "endedAt": "2026-08-03T12:10:00+09:00",
        "messages": [
            {
                "sourceMessageId": message_id,
                "role": "assistant",
                "messageType": "text",
                "content": content,
                "createdAt": "2026-08-03T12:05:00+09:00",
            }
        ],
        "commands": [],
        "changedFiles": [],
        "tests": [],
        "attachments": [],
    }
    return {
        "schemaVersion": "1.0",
        "captureId": capture_id,
        "sourceType": "codex",
        "captureType": "development_session",
        "captureDevice": "windows",
        "captureMethod": "windows_codex_wrapper",
        "projectId": "mde",
        "targetFolder": "40_Reference/Codex",
        "parentDocument": None,
        "capturedAt": "2026-08-03T12:10:00+09:00",
        "deviceId": "windows-test",
        "contentHash": digest(str(payload)),
        "metadata": {},
        "payload": payload,
    }


def excerpt(
    capture_id: str, content: str, *, project_id: str | None = "mde"
) -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "captureId": capture_id,
        "sourceType": "codex",
        "captureType": "clipboard_item",
        "captureDevice": "android",
        "captureMethod": "android_clipboard",
        "projectId": project_id,
        "targetFolder": "40_Reference",
        "parentDocument": None,
        "capturedAt": "2026-08-03T12:06:00+09:00",
        "deviceId": "android-test",
        "contentHash": digest(content),
        "metadata": {"sourceApp": "codex_android"},
        "payload": {
            "content": content,
            "title": "Codex excerpt",
            "mimeType": "text/plain",
            "language": "ko",
        },
    }


def client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            JsonShareStore(tmp_path / "data"),
            auto_process=False,
            note_store=ObsidianNoteStore(tmp_path / "vault"),
            mde_client=NullIndexer(),
        )
    )


def test_exact_hash_creates_one_confirmed_excerpt_relation(tmp_path: Path) -> None:
    content = (
        "동일한 Codex 공개 assistant 답변입니다. "
        "관계는 원본을 병합하지 않고 별도로 보존합니다."
    )
    api = client(tmp_path)

    assert (
        api.post("/api/v1/captures", json=session("cap_windows", content)).status_code
        == 200
    )
    assert (
        api.post("/api/v1/captures", json=excerpt("cap_android", content)).status_code
        == 200
    )
    response = api.get("/api/v1/captures/cap_android/relations?status=confirmed")

    assert response.status_code == 200
    relation = response.json()["relations"][0]
    assert relation["relationType"] == "excerpt_of"
    assert relation["fromCaptureId"] == "cap_android"
    assert relation["toCaptureId"] == "cap_windows"
    assert relation["matchMethod"] == "exact_message_hash"
    assert relation["evidence"]["matchedMessageId"] == "msg_1"
    assert "normalizedContent" not in relation["evidence"]


def test_equal_exact_candidates_remain_suggested(tmp_path: Path) -> None:
    content = (
        "반복되는 공개 Codex 답변이므로 서로 다른 두 세션 중 "
        "하나를 자동 선택하면 안 됩니다."
    )
    api = client(tmp_path)
    api.post("/api/v1/captures", json=session("cap_windows_a", content))
    api.post("/api/v1/captures", json=session("cap_windows_b", content))
    api.post("/api/v1/captures", json=excerpt("cap_android", content))

    response = api.get("/api/v1/captures/cap_android/relation-candidates")

    assert response.status_code == 200
    assert len(response.json()["candidates"]) == 2
    assert {item["status"] for item in response.json()["candidates"]} == {"suggested"}
    first, second = response.json()["candidates"]
    confirmed = api.post(f"/api/v1/capture-relations/{first['relationId']}/confirm")
    rejected = api.post(
        f"/api/v1/capture-relations/{second['relationId']}/reject",
        json={"rejectionReason": "different_session"},
    )
    removed = api.delete(f"/api/v1/capture-relations/{first['relationId']}")
    assert confirmed.json()["status"] == "confirmed"
    assert rejected.json()["status"] == "rejected"
    assert removed.json()["status"] == "removed"


def test_substring_and_contiguous_message_matching() -> None:
    matcher = CaptureRelationMatcher()
    first = "A" * 80
    second = "B" * 80
    combined = first + "\n" + second
    excerpt_record = {
        "captureId": "clip",
        "sourceType": "codex",
        "captureType": "clipboard_item",
        "captureDevice": "android",
        "capturedAt": "2026-08-03T12:05:00+09:00",
        "projectId": "mde",
        "sourceApp": "codex_android",
        "contentHash": digest(combined),
        "normalizedContent": combined,
    }
    session_record = {
        "captureId": "session",
        "sourceType": "codex",
        "captureType": "development_session",
        "captureDevice": "windows",
        "startedAt": "2026-08-03T12:00:00+09:00",
        "endedAt": "2026-08-03T12:10:00+09:00",
        "projectId": "mde",
        "clientType": "codex_app_server",
        "revision": 1,
        "messages": [
            {
                "messageId": "m1",
                "role": "assistant",
                "contentHash": digest(first),
                "normalizedContent": first,
                "createdAt": "2026-08-03T12:04:00+09:00",
            },
            {
                "messageId": "m2",
                "role": "assistant",
                "contentHash": digest(second),
                "normalizedContent": second,
                "createdAt": "2026-08-03T12:05:00+09:00",
            },
        ],
    }

    candidates = matcher.candidates(excerpt_record, [session_record])

    assert candidates[0].method == "contiguous_message_group"
    assert candidates[0].evidence.matched_message_ids == ["m1", "m2"]
    assert candidates[0].score >= 100


def test_short_partial_and_different_project_are_not_matched() -> None:
    matcher = CaptureRelationMatcher()
    clip = {
        "captureId": "clip",
        "sourceType": "codex",
        "captureType": "clipboard_item",
        "captureDevice": "android",
        "capturedAt": "2026-08-03T12:00:00+09:00",
        "projectId": "one",
        "contentHash": digest("short"),
        "normalizedContent": "short",
    }
    target = {
        "captureId": "session",
        "sourceType": "codex",
        "captureType": "development_session",
        "captureDevice": "windows",
        "startedAt": "2026-08-03T12:00:00+09:00",
        "projectId": "two",
        "messages": [
            {
                "messageId": "m",
                "role": "assistant",
                "contentHash": digest("short and more"),
                "normalizedContent": "short and more",
            }
        ],
    }
    assert matcher.candidates(clip, [target]) == []


def test_revision_without_message_marks_confirmed_relation_stale(
    tmp_path: Path,
) -> None:
    content = "revision 재검증에서 유지되어야 할 공개 assistant 답변입니다."
    api = client(tmp_path)
    original = session("cap_windows", content)
    api.post("/api/v1/captures", json=original)
    api.post("/api/v1/captures", json=excerpt("cap_android", content))
    changed = session("cap_windows", "완전히 교체된 다른 공개 답변입니다.")
    changed["payload"]["summary"] = "revision 2"

    response = api.post("/api/v1/captures", json=changed)
    relations = api.get("/api/v1/captures/cap_android/relations").json()["relations"]

    assert response.json()["revision"] == 2
    assert relations[0]["status"] == RelationStatus.STALE.value
    assert relations[0]["evidence"]["targetRevision"] == 2


def test_rejected_pair_is_not_suggested_again(tmp_path: Path) -> None:
    api = client(tmp_path / "api")
    content = (
        "사용자가 거절한 후보는 revision이나 재검색 때 "
        "반복 제안되면 안 되는 충분한 답변입니다."
    )
    api.post("/api/v1/captures", json=session("cap_windows", content))
    api.post("/api/v1/captures", json=excerpt("cap_android", content))
    # Exercise the repository/service directly with the API-created index.
    service = CaptureRelationService(
        CaptureRelationRepository(tmp_path / "api" / "data")
    )
    relation = service.relations_for("cap_android")[0]
    service.transition(
        relation.relation_id, RelationStatus.REJECTED, reason="different_session"
    )
    assert service.find_candidates("cap_android") == []


def test_backfill_dry_run_does_not_write_relations(tmp_path: Path) -> None:
    repository = CaptureRelationRepository(tmp_path)
    service = CaptureRelationService(repository)
    content = "C" * 120
    repository.upsert_capture(
        {
            "captureId": "clip",
            "sourceType": "codex",
            "captureType": "clipboard_item",
            "captureDevice": "android",
            "capturedAt": "2026-08-03T12:05:00+09:00",
            "projectId": "mde",
            "contentHash": digest(content),
            "normalizedContent": content,
        }
    )
    repository.upsert_capture(
        {
            "captureId": "session",
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "startedAt": "2026-08-03T12:00:00+09:00",
            "projectId": "mde",
            "revision": 1,
            "messages": [
                {
                    "messageId": "m",
                    "role": "assistant",
                    "contentHash": digest(content),
                    "normalizedContent": content,
                }
            ],
        }
    )

    report = service.backfill(dry_run=True)

    assert report["high"] == 1
    assert repository.relations() == []


def test_backfill_cli_dry_run_keeps_operational_relation_index_unchanged(
    tmp_path: Path, capsys
) -> None:
    data = tmp_path / "data"
    vault = tmp_path / "vault"
    repository = CaptureRelationRepository(data)
    content = "D" * 120
    repository.upsert_capture(
        {
            "captureId": "clip",
            "sourceType": "codex",
            "captureType": "clipboard_item",
            "captureDevice": "android",
            "capturedAt": "2026-08-03T12:05:00+09:00",
            "projectId": "mde",
            "contentHash": digest(content),
            "normalizedContent": content,
        }
    )
    repository.upsert_capture(
        {
            "captureId": "session",
            "sourceType": "codex",
            "captureType": "development_session",
            "captureDevice": "windows",
            "startedAt": "2026-08-03T12:00:00+09:00",
            "projectId": "mde",
            "revision": 1,
            "messages": [
                {
                    "messageId": "m",
                    "role": "assistant",
                    "contentHash": digest(content),
                    "normalizedContent": content,
                }
            ],
        }
    )

    result = cli_main(
        [
            "capture-relations",
            "backfill",
            "--data-dir",
            str(data),
            "--vault-dir",
            str(vault),
            "--dry-run",
        ]
    )

    assert result == 0
    assert '"high": 1' in capsys.readouterr().out
    assert not (data / "capture-relations-v1.json").exists()
