[CmdletBinding()]
param(
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$mdeExecutable = Join-Path $repositoryRoot ".venv\Scripts\mde.exe"
$capturePython = Join-Path $repositoryRoot "apps\autoknowledge-lite\.venv\Scripts\python.exe"
$viewerUrl = "http://127.0.0.1:8765/"
$captureStatusUrl = "http://127.0.0.1:8000/v1/status"

if (-not (Test-Path -LiteralPath $mdeExecutable)) {
    throw "MDE 실행 파일을 찾을 수 없습니다. 저장소 루트에서 uv sync --locked를 먼저 실행하세요."
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri $captureStatusUrl -TimeoutSec 2 | Out-Null
}
catch {
    if (-not (Test-Path -LiteralPath $capturePython)) {
        throw "AutoKnowledge Lite 실행 환경을 찾을 수 없습니다. apps/autoknowledge-lite에서 uv sync를 실행하세요."
    }
    Start-Process `
        -FilePath $capturePython `
        -ArgumentList @("-m", "uvicorn", "autoknowledge_lite.api:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory (Join-Path $repositoryRoot "apps\autoknowledge-lite") `
        -WindowStyle Hidden
    $captureReady = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $captureStatusUrl -TimeoutSec 2 | Out-Null
            $captureReady = $true
            break
        }
        catch {
        }
    }
    if (-not $captureReady) {
        throw "AutoKnowledge Capture 서버가 시작되지 않았습니다."
    }
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri $viewerUrl -TimeoutSec 2 | Out-Null
}
catch {
    Start-Process -FilePath $mdeExecutable -ArgumentList @("knowledge", "serve", "--no-open") -WorkingDirectory $repositoryRoot -WindowStyle Hidden
    $ready = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        Start-Sleep -Milliseconds 250
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $viewerUrl -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        }
        catch {
        }
    }
    if (-not $ready) {
        throw "Knowledge Viewer 서버가 시작되지 않았습니다."
    }
}

if ($NoOpen) {
    return
}

$edgeCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

if ($edgeCandidates.Count -gt 0) {
    Start-Process -FilePath $edgeCandidates[0] -ArgumentList "--app=$viewerUrl"
}
else {
    Start-Process $viewerUrl
}
