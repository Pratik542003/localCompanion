param(
    [string]$ServerPath = "",
    [int]$Port = 8082
)

$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskModel = Join-Path $taskRoot "data\models\Qwen3-4B-Q4_K_M.gguf"
$taskRuntime = Join-Path $taskRoot "data\runtime"
$taskUrl = "http://127.0.0.1:$Port"

if (-not (Test-Path -LiteralPath $taskModel)) {
    throw "Qwen model is missing: $taskModel"
}

function Test-QwenReady {
    try {
        $taskHealth = Invoke-RestMethod "$taskUrl/health" -TimeoutSec 2
        $taskModels = Invoke-RestMethod "$taskUrl/v1/models" -TimeoutSec 2
        return $taskHealth.status -eq "ok" -and @($taskModels.data.id) -contains "qwen3-4b"
    } catch {
        return $false
    }
}

if (Test-QwenReady) {
    Write-Output "Qwen3 is already ready at $taskUrl"
    exit 0
}

# Do not replace an unrelated service listening on this port.
$taskConnection = New-Object System.Net.Sockets.TcpClient
try {
    $taskConnection.Connect("127.0.0.1", $Port)
    throw "Port $Port is already in use by a different or still-loading service."
} catch [System.Net.Sockets.SocketException] {
    # A closed port is available for our server.
} finally {
    $taskConnection.Dispose()
}

if (-not $ServerPath) {
    foreach ($taskCandidate in @("C:\llama-cpp\models\llama-server.exe", "C:\llama-cpp\llama-server.exe")) {
        if (Test-Path -LiteralPath $taskCandidate) {
            $ServerPath = $taskCandidate
            break
        }
    }
}
if (-not $ServerPath -or -not (Test-Path -LiteralPath $ServerPath)) {
    throw "llama-server.exe was not found. Pass -ServerPath with its location."
}

New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskOldTemplate = $env:LLAMA_ARG_CHAT_TEMPLATE_KWARGS
try {
    $env:LLAMA_ARG_CHAT_TEMPLATE_KWARGS = '{"enable_thinking":false}'
    $taskArgs = @("-m", ('"' + $taskModel + '"'), "--host", "127.0.0.1", "--port", "$Port",
                  "--alias", "qwen3-4b", "-c", "8192", "-t", "8", "--jinja",
                  "--reasoning", "off", "--reasoning-budget", "0", "--reasoning-format", "deepseek")
    $taskProcess = Start-Process -FilePath $ServerPath -ArgumentList $taskArgs -WindowStyle Hidden `
        -WorkingDirectory (Split-Path -Parent $ServerPath) -PassThru `
        -RedirectStandardOutput (Join-Path $taskRuntime "qwen.stdout.log") `
        -RedirectStandardError (Join-Path $taskRuntime "qwen.stderr.log")
} finally {
    $env:LLAMA_ARG_CHAT_TEMPLATE_KWARGS = $taskOldTemplate
}
$taskProcess.Id | Set-Content (Join-Path $taskRuntime "qwen.pid")
Write-Output "Loading Qwen3 (PID $($taskProcess.Id))..."
$taskDeadline = (Get-Date).AddSeconds(120)
while ((Get-Date) -lt $taskDeadline) {
    if (Test-QwenReady) {
        Write-Output "Qwen3 is ready at $taskUrl"
        exit 0
    }
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) {
        throw "Qwen server exited. See data\runtime\qwen.stderr.log."
    }
    Start-Sleep -Seconds 1
}
throw "Qwen is still loading. See data\runtime\qwen.stderr.log."
