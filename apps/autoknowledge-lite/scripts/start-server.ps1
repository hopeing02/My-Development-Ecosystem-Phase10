$appRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonPath = Join-Path $appRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $appRoot "logs"
$serverLog = Join-Path $logDirectory "server-autostart.log"

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

try {
    $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
    if ($listeners.Port -contains 8000) {
        exit 0
    }

    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python runtime not found. Run 'uv sync --project apps/autoknowledge-lite' first."
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value "$timestamp Starting AutoKnowledge Lite."
    Set-Location -LiteralPath $appRoot
    & $pythonPath -m uvicorn autoknowledge_lite.api:app --host 0.0.0.0 --port 8000 2>&1 |
        ForEach-Object { Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value $_ }
    exit $LASTEXITCODE
}
catch {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value "$timestamp Startup failed: $($_.Exception.Message)"
    exit 1
}
