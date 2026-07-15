from mde.cli import main


def test_plugin_list(capsys) -> None:
    assert main(["plugin", "list"]) == 0
    output = capsys.readouterr().out
    assert "core" in output
    assert "testing" in output
    assert "git" in output
