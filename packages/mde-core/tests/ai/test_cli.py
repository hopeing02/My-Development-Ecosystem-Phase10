from mde.cli import main


def test_ai_list_command(capsys) -> None:
    assert main(["ai", "list"]) == 0
    assert capsys.readouterr().out.strip().splitlines() == [
        "claude",
        "gemini",
        "local",
        "mock",
        "openai",
    ]


def test_ai_check_mock_provider(capsys) -> None:
    assert main(["ai", "check", "--provider", "mock"]) == 0
    assert capsys.readouterr().out.strip() == "AI provider ready: mock"


def test_ai_check_openai_requires_api_key(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["ai", "check", "--provider", "openai"]) == 1
    assert "OPENAI_API_KEY" in capsys.readouterr().out


def test_ai_check_openai_accepts_api_key(monkeypatch, capsys) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert main(["ai", "check", "--provider", "openai"]) == 0
    assert capsys.readouterr().out.strip().splitlines() == [
        "AI provider ready: openai",
        "Model: gpt-5-mini",
        "API key env: OPENAI_API_KEY",
    ]
