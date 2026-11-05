"""Verify development orchestration with fake commands, never a real Codex call."""

import shutil
import subprocess
from pathlib import Path

import pytest

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell is required for the runner")
@pytest.mark.parametrize("failure", ["none", "codex", "pytest", "ruff", "black"])
def test_development_runner_stops_at_first_error(tmp_path: Path, failure: str):
    repo = tmp_path / "fake repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("", encoding="utf-8")
    runner = (
        Path(__file__).resolve().parents[3]
        / "11_AI_Request"
        / "EBOOK_AI_STEP01_Run.ps1"
    )
    harness = tmp_path / "harness.ps1"
    harness.write_text(
        r"""
param([string]$Runner, [string]$Repo, [string]$Failure)
$global:EbookTestLog = Join-Path $Repo 'commands.txt'
function git {
    if ($args -contains 'rev-parse') { Write-Output $Repo }
    $global:LASTEXITCODE = 0
}
function codex {
    $input | Out-String | Set-Content -LiteralPath (Join-Path $Repo 'prompt.txt') -Encoding UTF8
    Add-Content -LiteralPath $global:EbookTestLog -Value 'codex' -Encoding UTF8
    $global:LASTEXITCODE = 0
    if ($Failure -eq 'codex') { $global:LASTEXITCODE = 9 }
}
function uv {
    $tool = $args[2]
    Add-Content -LiteralPath $global:EbookTestLog -Value $tool -Encoding UTF8
    $global:LASTEXITCODE = 0
    if ($Failure -eq $tool) { $global:LASTEXITCODE = 9 }
}
try { & $Runner -MdeRepoRoot $Repo; exit 0 }
catch { Write-Output $_.Exception.Message; exit 1 }
""",
        encoding="utf-8-sig",
    )
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(harness),
            "-Runner",
            str(runner),
            "-Repo",
            str(repo),
            "-Failure",
            failure,
        ],
        capture_output=True,
        timeout=30,
    )
    steps = ["codex", "python", "pytest", "ruff", "black"]
    expected = steps if failure == "none" else steps[: steps.index(failure) + 1]
    assert (repo / "commands.txt").exists(), (result.stdout, result.stderr)
    assert (repo / "commands.txt").read_text(
        encoding="utf-8-sig"
    ).splitlines() == expected
    assert result.returncode == (0 if failure == "none" else 1), result.stdout
    received = (repo / "prompt.txt").read_text(encoding="utf-8-sig")
    original = runner.with_name("EBOOK_AI_STEP01_CODEX_PROMPT.md").read_text(
        encoding="utf-8-sig"
    )
    assert received.strip() == original.strip()
