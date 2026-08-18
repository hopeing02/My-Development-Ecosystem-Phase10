[CmdletBinding()]
param(
    [string]$HostAddress = "0.0.0.0",
    [string]$HealthAddress = "127.0.0.1",
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$mdeExecutable = Join-Path $repositoryRoot ".venv\Scripts\mde.exe"
$capturePython = Join-Path $repositoryRoot "apps\autoknowledge-lite\.venv\Scripts\python.exe"
$logDirectory = Join-Path $repositoryRoot "logs"
$supervisorLog = Join-Path $logDirectory "knowledge-viewer-supervisor.log"
$stdoutLog = Join-Path $logDirectory "knowledge-viewer.out.log"
$stderrLog = Join-Path $logDirectory "knowledge-viewer.err.log"
$captureStdoutLog = Join-Path $logDirectory "autoknowledge-capture.out.log"
$captureStderrLog = Join-Path $logDirectory "autoknowledge-capture.err.log"

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

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

if (-not (Test-Path -LiteralPath $mdeExecutable)) {
    throw "MDE executable was not found: $mdeExecutable"
}

function Write-SupervisorLog {
    param([string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    Add-Content -LiteralPath $supervisorLog -Encoding UTF8 -Value "$timestamp $Message"
}

function Test-ViewerHealth {
    $request = $null
    $response = $null
    try {
        $request = [System.Net.HttpWebRequest]::Create(
            "http://${HealthAddress}:$Port/"
        )
        $request.Proxy = $null
        $request.Timeout = 3000
        $request.ReadWriteTimeout = 3000
        $response = $request.GetResponse()
        return [int]$response.StatusCode -eq 200
    }
    catch {
        return $false
    }
    finally {
        if ($response) {
            $response.Dispose()
        }
    }
}

function Test-CaptureHealth {
    try {
        Invoke-WebRequest `
            -UseBasicParsing `
            -Uri "http://127.0.0.1:8000/v1/status" `
            -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Start-CaptureProcess {
    if (-not (Test-Path -LiteralPath $capturePython)) {
        Write-SupervisorLog "Capture Python environment is unavailable: $capturePython"
        return $null
    }
    Write-SupervisorLog "Starting AutoKnowledge Capture API on ${HostAddress}:8000."
    return Start-Process `
        -FilePath $capturePython `
        -ArgumentList @(
            "-m", "uvicorn", "autoknowledge_lite.api:app",
            "--host", $HostAddress, "--port", "8000"
        ) `
        -WorkingDirectory (Join-Path $repositoryRoot "apps\autoknowledge-lite") `
        -WindowStyle Hidden `
        -RedirectStandardOutput $captureStdoutLog `
        -RedirectStandardError $captureStderrLog `
        -PassThru
}

function Wait-ViewerHealth {
    param([int]$TimeoutSeconds = 60)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (Test-ViewerHealth) {
            return $true
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Stop-ManagedViewerListeners {
    $listeners = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue
    $processIds = $listeners |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        $process = Get-CimInstance `
            -ClassName Win32_Process `
            -Filter "ProcessId = $processId" `
            -ErrorAction SilentlyContinue
        if (
            $process.CommandLine -and
            $process.CommandLine.Contains($mdeExecutable) -and
            $process.CommandLine -match "knowledge\s+serve" -and
            $process.CommandLine -match "--port\s+$Port(?:\s|$)"
        ) {
            Write-SupervisorLog "Stopping unhealthy Viewer process $processId."
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
    if ($processIds) {
        Start-Sleep -Seconds 1
    }
}

function Start-ViewerProcess {
    Write-SupervisorLog "Starting Knowledge Viewer on ${HostAddress}:$Port."
    return Start-Process `
        -FilePath $mdeExecutable `
        -ArgumentList @(
            "knowledge",
            "serve",
            "--host",
            $HostAddress,
            "--port",
            $Port,
            "--no-open"
        ) `
        -WorkingDirectory $repositoryRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -PassThru
}

while ($true) {
    if (-not (Test-CaptureHealth)) {
        $captureServer = Start-CaptureProcess
        if ($captureServer) {
            for ($attempt = 0; $attempt -lt 20; $attempt++) {
                Start-Sleep -Milliseconds 500
                if (Test-CaptureHealth) {
                    Write-SupervisorLog "AutoKnowledge Capture API is healthy."
                    break
                }
            }
        }
    }
    if (Test-ViewerHealth) {
        Start-Sleep -Seconds 10
        continue
    }

    Write-SupervisorLog "HTTP health check failed; restarting the managed Viewer."
    Stop-ManagedViewerListeners
    try {
        $server = Start-ViewerProcess
        if (Wait-ViewerHealth) {
            Write-SupervisorLog (
                "Knowledge Viewer is healthy on ${HostAddress}:$Port " +
                "through ${HealthAddress}:$Port."
            )
        }
        elseif ($server.HasExited) {
            Write-SupervisorLog (
                "Knowledge Viewer exited during startup with code " +
                "$($server.ExitCode)."
            )
        }
        else {
            Write-SupervisorLog "Knowledge Viewer did not become healthy within 60 seconds."
        }
    }
    catch {
        Write-SupervisorLog "Knowledge Viewer launch failed: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds 10
}
