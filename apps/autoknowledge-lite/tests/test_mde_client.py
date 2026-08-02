import json
import subprocess

import pytest

from autoknowledge_lite.mde_client import (
    MDEClientError,
    MDEKnowledgeClient,
    command_from_environment,
)


def test_client_uses_argument_array_and_validates_json_contract() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "apiVersion": "1",
                    "success": True,
                    "sources": [
                        {
                            "id": "ks-001",
                            "name": "personal",
                            "category": "personal",
                            "sourceType": "obsidian",
                            "enabled": True,
                            "sensitive": True,
                            "writableByCaptureApp": True,
                        }
                    ],
                }
            ),
            "",
        )

    sources = MDEKnowledgeClient(["mde"], runner=runner).list_sources()

    assert sources[0].name == "personal"
    command, options = calls[0]
    assert command == ["mde", "knowledge", "list", "--format", "json"]
    assert options["shell"] is False
    assert options["timeout"] == 30
    assert options["encoding"] == "utf-8"
    assert options["env"]["PYTHONIOENCODING"] == "utf-8"


@pytest.mark.parametrize(
    ("stdout", "code"),
    [
        (None, "INVALID_RESPONSE"),
        ("", "INVALID_RESPONSE"),
        ("not-json", "INVALID_RESPONSE"),
        ('{"success":true,"apiVersion":"2"}', "UNSUPPORTED_API_VERSION"),
    ],
)
def test_client_rejects_invalid_or_incompatible_response(
    stdout: str | None, code: str
) -> None:
    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout, "")

    with pytest.raises(MDEClientError) as error:
        MDEKnowledgeClient(["mde"], runner=runner).integration_info()
    assert error.value.code == code


def test_command_configuration_is_a_json_argument_array(monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTOKNOWLEDGE_MDE_COMMAND",
        '["uv","run","--project","C:\\\\Projects\\\\MDE","mde"]',
    )
    assert command_from_environment() == [
        "uv",
        "run",
        "--project",
        "C:\\Projects\\MDE",
        "mde",
    ]


def test_client_searches_documents_and_links_child_with_json_contract() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if "search" in command:
            data = {
                "apiVersion": "1",
                "success": True,
                "documents": [
                    {
                        "id": "ks-002::Parent.md",
                        "sourceId": "ks-002",
                        "title": "상위 주제",
                        "relativePath": "Parent.md",
                        "snippet": "설명",
                    }
                ],
            }
        else:
            data = {
                "apiVersion": "1",
                "success": True,
                "result": {"fileSaved": True, "alreadyLinked": False},
            }
        return subprocess.CompletedProcess(command, 0, json.dumps(data), "")

    client = MDEKnowledgeClient(["mde"], runner=runner)
    documents = client.search_documents("personal", "상위", limit=10)
    linked = client.link_child(
        "personal", "ks-002::Parent.md", "ks-002::Child.md"
    )

    assert documents[0].title == "상위 주제"
    assert documents[0].relative_path == "Parent.md"
    assert linked["fileSaved"] is True
    assert calls[0] == [
        "mde",
        "knowledge",
        "search",
        "상위",
        "--source",
        "personal",
        "--include-sensitive",
        "--limit",
        "10",
        "--format",
        "json",
    ]
    assert calls[1][-2:] == ["--format", "json"]
