#requires -Version 5.1
<#
.SYNOPSIS
Run EBOOK-AI-01 development and external checks without automatic commit/push.
.PARAMETER ValidateOnly
Run external checks against existing code without invoking Codex.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MdeRepoRoot,
    [switch]$ValidateOnly
)

$ErrorActionPreference = 'Stop'
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
    $PSNativeCommandUseErrorActionPreference = $false
}

foreach ($command in @('git', 'uv')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "$command command not found. Install it and check PATH."
    }
}
if (-not $ValidateOnly -and -not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw 'Codex CLI not found. Check installation and login.'
}
$repoRoot = (Resolve-Path -LiteralPath $MdeRepoRoot).Path
$promptPath = Join-Path $PSScriptRoot 'EBOOK_AI_STEP01_CODEX_PROMPT.md'
if (-not $ValidateOnly -and -not (Test-Path -LiteralPath $promptPath -PathType Leaf)) {
    throw "Prompt file not found: $promptPath"
}

$previousOutputEncoding = $OutputEncoding
$previousConsoleEncoding = [Console]::OutputEncoding
Push-Location -LiteralPath $repoRoot
try {
    $gitRoot = & git rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0) { throw 'Not a Git working tree.' }
    if ([IO.Path]::GetFullPath($gitRoot) -ne [IO.Path]::GetFullPath($repoRoot)) {
        throw 'MdeRepoRoot must point to the repository root.'
    }
    if (-not (Test-Path -LiteralPath 'pyproject.toml' -PathType Leaf)) {
        throw 'MDE pyproject.toml not found.'
    }

    if (-not $ValidateOnly) {
        $OutputEncoding = New-Object System.Text.UTF8Encoding($false)
        [Console]::OutputEncoding = $OutputEncoding
        $promptText = Get-Content -LiteralPath $promptPath -Raw -Encoding UTF8
        if ([string]::IsNullOrWhiteSpace($promptText)) { throw 'Prompt file is empty.' }
        $promptText | & codex exec --sandbox workspace-write -
        if ($LASTEXITCODE -ne 0) { throw 'Codex development failed.' }
    }

    & uv run --locked python -c "import sys; assert sys.version_info >= (3, 12), 'Python 3.12+ required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python environment check failed.' }
    & uv run --locked pytest apps/ebook_ai/tests -q
    if ($LASTEXITCODE -ne 0) { throw 'Ebook tests failed.' }
    & uv run --locked ruff check apps/ebook_ai
    if ($LASTEXITCODE -ne 0) { throw 'Ruff check failed.' }
    & uv run --locked black --check --workers 1 apps/ebook_ai
    if ($LASTEXITCODE -ne 0) { throw 'Black check failed.' }
    & git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Git diff whitespace check failed.' }

    # git diff does not inspect untracked files; check the new package/records too.
    $newFiles = @(& git -c core.quotePath=false ls-files --others --exclude-standard -- apps/ebook_ai 11_AI_Request/EBOOK_AI_STEP01_CODEX_PROMPT.md 11_AI_Request/EBOOK_AI_STEP01_Run.ps1 docs/15_projects/ebook_ai)
    if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate new ebook files.' }
    foreach ($newFile in $newFiles) {
        & git -c core.autocrlf=false diff --no-index --check -- NUL $newFile
        if ($LASTEXITCODE -gt 1) { throw "New file whitespace check failed: $newFile" }
    }

    Write-Host 'External checks passed. STEP awaits user review of generated files.'
    Write-Host 'No automatic commit/push was run by this script.'
}
finally {
    $OutputEncoding = $previousOutputEncoding
    [Console]::OutputEncoding = $previousConsoleEncoding
    Pop-Location
}
