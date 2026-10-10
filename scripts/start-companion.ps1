$ErrorActionPreference = "Stop"
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskRuntime = Join-Path $taskRoot "data\runtime"
$taskPython = Join-Path $taskRoot ".venv\Scripts\python.exe"

function Test-CompanionReady {
    try {
        $taskHealth = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2
        $taskVoice = Invoke-RestMethod "http://127.0.0.1:8000/api/voice" -TimeoutSec 5
        return $taskHealth.status -eq "healthy" -and $taskHealth.model -eq "qwen3-4b" -and $taskVoice.speech_to_text -and $taskVoice.text_to_speech
    } catch {
        return $false
    }
}

# Allow an existing reload-enabled app to pick up the new settings.
$taskConnection = New-Object System.Net.Sockets.TcpClient
$taskOccupied = $false
try {
    $taskConnection.Connect("127.0.0.1", 8000)
    $taskOccupied = $true
} catch [System.Net.Sockets.SocketException] {
} finally {
    $taskConnection.Dispose()
}
if ($taskOccupied) {
    for ($taskAttempt = 0; $taskAttempt -lt 15; $taskAttempt++) {
        if (Test-CompanionReady) {
            Write-Output "Companion is ready at http://localhost:8000"
            exit 0
        }
        Start-Sleep -Seconds 1
    }
    throw "Port 8000 is occupied by another service or a companion needing a restart."
}

New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskProcess = Start-Process -FilePath $taskPython -WindowStyle Hidden -PassThru `
    -WorkingDirectory $taskRoot `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -RedirectStandardOutput (Join-Path $taskRuntime "companion.stdout.log") `
    -RedirectStandardError (Join-Path $taskRuntime "companion.stderr.log")
$taskProcess.Id | Set-Content (Join-Path $taskRuntime "companion.pid")
for ($taskAttempt = 0; $taskAttempt -lt 30; $taskAttempt++) {
    if (Test-CompanionReady) {
        Write-Output "Companion is ready at http://localhost:8000"
        exit 0
    }
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) { throw "Companion exited. See data\runtime\companion.stderr.log." }
    Start-Sleep -Seconds 1
}
throw "Companion did not become ready. See data\runtime\companion.stderr.log."
