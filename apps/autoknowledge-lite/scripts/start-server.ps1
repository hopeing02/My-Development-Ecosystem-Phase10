$appRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonPath = Join-Path $appRoot ".venv\Scripts\python.exe"
$logDirectory = Join-Path $appRoot "logs"
$serverLog = Join-Path $logDirectory "server-autostart.log"

foreach ($variableName in @(
    "AUTOKNOWLEDGE_CONTROL_API_KEY",
    "AUTOKNOWLEDGE_VIEWER_URL",
    "MDE_CODEX_EXECUTABLE",
    "MDE_CODEX_CONVERSATION_CAPTURE"
)) {
    $userValue = [Environment]::GetEnvironmentVariable($variableName, "User")
    if (-not [string]::IsNullOrWhiteSpace($userValue)) {
        Set-Item -Path "Env:$variableName" -Value $userValue
    }
}

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Python runtime not found. Run 'uv sync --project apps/autoknowledge-lite' first."
}

while ($true) {
    try {
        $listeners = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners()
        if ($listeners.Port -contains 8000) {
            Start-Sleep -Seconds 10
            continue
        }

        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value "$timestamp Starting AutoKnowledge Lite."
        Set-Location -LiteralPath $appRoot
        & $pythonPath -m uvicorn autoknowledge_lite.api:app --host 0.0.0.0 --port 8000 2>&1 |
            ForEach-Object { Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value $_ }
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value "$timestamp Server exited with code $LASTEXITCODE; retrying."
    }
    catch {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -LiteralPath $serverLog -Encoding UTF8 -Value "$timestamp Startup failed: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 5
}
