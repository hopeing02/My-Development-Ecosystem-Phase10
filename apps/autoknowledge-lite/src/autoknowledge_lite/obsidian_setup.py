"""Idempotent Obsidian core settings, templates and Bases."""

from __future__ import annotations

import json
from pathlib import Path

REQUIRED_CORE_PLUGINS: tuple[str, ...] = (
    "backlink",
    "outgoing-link",
    "graph",
    "properties",
    "bases",
    "templates",
)

GRAPH_CONFIG: dict[str, object] = {
    "collapse-filter": False,
    "search": '-path:"90_Archive" -tag:#integration-test',
    "showTags": False,
    "showAttachments": False,
    "hideUnresolved": True,
    "showOrphans": True,
    "collapse-color-groups": False,
    "colorGroups": [
        {"query": 'path:"10_Life"', "color": {"a": 1, "rgb": 5025616}},
        {"query": 'path:"20_Learning"', "color": {"a": 1, "rgb": 2201331}},
        {"query": 'path:"30_Interests"', "color": {"a": 1, "rgb": 10233776}},
        {"query": 'path:"40_Reference"', "color": {"a": 1, "rgb": 16750592}},
        {"query": 'path:"AutoKnowledge"', "color": {"a": 1, "rgb": 6323595}},
    ],
    "showArrow": True,
}

KNOWLEDGE_TEMPLATE = """---
aliases: []
tags: []
type: note
status: to-review
reviewed: false
topics: []
---

# {{title}}

## Summary

## Key Points

## Original Content

## 연결

- 상위 주제:
"""

BASES: dict[str, str] = {
    "받은함.base": """filters:
  and:
    - 'file.ext == "md"'
    - 'file.name != "README"'
    - or:
        - 'file.inFolder("00_Inbox")'
        - 'status == "to-review"'
properties:
  file.name:
    displayName: 노트
  status:
    displayName: 상태
  type:
    displayName: 종류
  topics:
    displayName: 주제
  received_at:
    displayName: 저장 시각
views:
  - type: table
    name: 받은함
    order:
      - file.name
      - status
      - type
      - topics
      - received_at
""",
    "최근 자료.base": """filters:
  and:
    - 'file.ext == "md"'
    - 'received_at != null'
properties:
  file.name:
    displayName: 노트
  received_at:
    displayName: 저장 시각
  type:
    displayName: 종류
  topics:
    displayName: 주제
views:
  - type: table
    name: 최근 자료
    order:
      - file.name
      - received_at
      - type
      - topics
""",
    "미검토 자료.base": """filters:
  and:
    - 'file.ext == "md"'
    - 'reviewed == false'
properties:
  file.name:
    displayName: 노트
  reviewed:
    displayName: 검토
  status:
    displayName: 상태
  topics:
    displayName: 주제
views:
  - type: table
    name: 미검토 자료
    order:
      - file.name
      - reviewed
      - status
      - topics
""",
    "주제별 자료.base": """filters:
  and:
    - 'file.ext == "md"'
    - 'topics != null'
properties:
  file.name:
    displayName: 노트
  topics:
    displayName: 주제
  type:
    displayName: 종류
  status:
    displayName: 상태
views:
  - type: table
    name: 주제별 자료
    groupBy:
      property: topics
      direction: ASC
    order:
      - file.name
      - topics
      - type
      - status
""",
    "중복 후보.base": """filters:
  and:
    - 'file.ext == "md"'
    - or:
        - 'status == "possible-duplicate"'
        - 'status == "duplicate"'
properties:
  file.name:
    displayName: 노트
  status:
    displayName: 상태
  canonical:
    displayName: 대표 정리본
views:
  - type: table
    name: 중복 후보
    order:
      - file.name
      - status
      - canonical
""",
}

DASHBOARD = """# Knowledge Dashboard

상위 지도: [[_Home]]

## 받은함

![[Bases/받은함.base#받은함]]

## 최근 자료

![[Bases/최근 자료.base#최근 자료]]

## 미검토 자료

![[Bases/미검토 자료.base#미검토 자료]]

## 주제별 자료

![[Bases/주제별 자료.base#주제별 자료]]

## 중복 후보

![[Bases/중복 후보.base#중복 후보]]
"""


def setup_obsidian(vault: Path, *, apply: bool) -> tuple[Path, ...]:
    """Preview or apply managed Obsidian files without replacing user settings."""

    vault = vault.resolve()
    if not vault.is_dir() or not (vault / ".git").is_dir():
        raise ValueError("Vault must be an existing Git repository.")

    desired = _desired_files(vault)
    changed = tuple(
        path
        for path, content in desired.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    )
    if apply:
        for path in changed:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(desired[path], encoding="utf-8")
    return changed


def _desired_files(vault: Path) -> dict[Path, str]:
    obsidian = vault / ".obsidian"
    core_plugins_path = obsidian / "core-plugins.json"
    existing_plugins = _read_json_list(core_plugins_path)
    plugins = list(existing_plugins)
    for plugin in REQUIRED_CORE_PLUGINS:
        if plugin not in plugins:
            plugins.append(plugin)

    templates_path = obsidian / "templates.json"
    templates_config = _read_json_object(templates_path)
    templates_config.setdefault("folder", "Templates")

    desired = {
        core_plugins_path: _json_text(plugins),
        templates_path: _json_text(templates_config),
        vault / "Templates" / "Knowledge Note.md": KNOWLEDGE_TEMPLATE,
        vault / "Knowledge Dashboard.md": DASHBOARD,
    }
    graph_path = obsidian / "graph.json"
    if graph_path.exists():
        desired[graph_path] = graph_path.read_text(encoding="utf-8")
    else:
        desired[graph_path] = _json_text(GRAPH_CONFIG)
    for name, content in BASES.items():
        desired[vault / "Bases" / name] = content
    return desired


def _read_json_list(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


def _read_json_object(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, dict) else {}


def _json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
