from __future__ import annotations

from datetime import datetime, timezone

from autoknowledge_lite.knowledge_graph import (
    build_graph_metadata,
    metadata_for_record,
    normalize_tag,
    organize_note,
    parse_note,
)
from autoknowledge_lite.models import KnowledgeAnalysis, ShareRecord


def test_normalize_tag_uses_obsidian_compatible_characters() -> None:
    assert normalize_tag("Android Studio") == "android-studio"
    assert normalize_tag(" 오픈소스 LLM ") == "오픈소스-llm"
    assert normalize_tag("Project / AutoKnowledge") == "project/autoknowledge"
    assert normalize_tag("1984") == "topic-1984"


def test_build_metadata_classifies_topics_and_removes_tag_duplicates() -> None:
    metadata = build_graph_metadata(
        title="내부 소형 모델",
        summary="로컬 RAG와 QLoRA를 결합한다.",
        tags=["로컬 RAG", "QLoRA", "qlora"],
        folder="20_Learning",
    )

    assert metadata.tags == ("로컬-rag", "qlora")
    assert metadata.aliases == ("로컬 rag · qlora",)
    assert metadata.note_type == "learning"
    assert metadata.status == "to-review"
    assert metadata.topics == ("MOC - 로컬 AI와 스마트홈",)


def test_metadata_for_record_uses_analysis() -> None:
    record = ShareRecord(
        job_id="12345678-0000-0000-0000-000000000000",
        received_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        content="본문",
        title="Android 빌드",
        target_folder="40_Reference",
        analysis=KnowledgeAnalysis(
            summary="Gradle로 APK를 빌드한다.",
            key_points=["프로젝트를 동기화한다."],
            tags=["Android Studio", "APK"],
            provider="test",
        ),
    )

    metadata = metadata_for_record(record)

    assert metadata.tags == ("android-studio", "apk")
    assert metadata.note_type == "reference"
    assert metadata.topics == ("MOC - Android 개발",)


def test_organize_note_preserves_body_and_is_idempotent() -> None:
    original = """---
title: "Android 빌드"
source_url: ""
received_at: "2026-07-24T00:00:00+00:00"
tags:
  - "Android Studio"
  - "APK"
---

# Android 빌드

## Summary

Gradle로 APK를 빌드한다.

## Original Content

보존해야 하는 원문입니다.
"""

    first = organize_note(original, folder="40_Reference")
    second = organize_note(first, folder="40_Reference")
    parsed = parse_note(first)

    assert second == first
    assert parsed.properties["aliases"] == ["android studio · apk"]
    assert parsed.properties["tags"] == ["android-studio", "apk"]
    assert parsed.properties["topics"] == ["[[MOC - Android 개발]]"]
    assert "보존해야 하는 원문입니다." in parsed.body
    assert parsed.body.count("## 연결") == 1
    assert "[[MOC - Android 개발]]" in parsed.body


def test_organize_note_marks_duplicate_without_deleting_content() -> None:
    original = """---
title: "같은 제목"
tags:
  - "GitHub"
---

# 같은 제목

원문
"""

    updated = organize_note(
        original,
        folder="AutoKnowledge",
        canonical="대표-노트",
        duplicate_status="possible-duplicate",
    )
    parsed = parse_note(updated)

    assert parsed.properties["status"] == "possible-duplicate"
    assert parsed.properties["canonical"] == "[[대표-노트]]"
    assert "원문" in parsed.body
    assert "- 대표 정리본: [[대표-노트]]" in parsed.body
