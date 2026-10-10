$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$binary = 'C:\whisper-cpp\Release\whisper-server.exe'
$model = 'C:\whisper-cpp\models\ggml-base.en.bin'
$runtime = Join-Path $projectRoot 'data\runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
function Test-Whisper {
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8081/health' -TimeoutSec 3
        return $health.status -eq 'ok'
    } catch { return $false }
}
if (Test-Whisper) { Write-Host '[OK] Local Whisper is already running.'; exit 0 }
$connection = New-Object System.Net.Sockets.TcpClient
$occupied = $false
try { $connection.Connect('127.0.0.1', 8081); $occupied = $true } catch [System.Net.Sockets.SocketException] {} finally { $connection.Dispose() }
if ($occupied) { throw 'Port 8081 is occupied by a service that is not healthy. Check it before restarting Whisper.' }
if (!(Test-Path -LiteralPath $binary) -or !(Test-Path -LiteralPath $model)) {
    throw 'Whisper server or model is missing from C:\whisper-cpp.'
}
$arguments = @('-m', ('"' + $model + '"'), '--host', '127.0.0.1', '--port', '8081', '-t', '8')
$process = Start-Process -FilePath $binary -ArgumentList $arguments -WorkingDirectory (Split-Path $binary) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'whisper.stdout.log') -RedirectStandardError (Join-Path $runtime 'whisper.stderr.log')
$process.Id | Set-Content (Join-Path $runtime 'whisper.pid')
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if (Test-Whisper) { Write-Host '[OK] Local Whisper started on port 8081.'; exit 0 }
    $process.Refresh()
    if ($process.HasExited) { throw 'Whisper exited. Check data\runtime\whisper.stderr.log.' }
    Start-Sleep -Milliseconds 1000
}
throw 'Whisper startup timed out. Check data\runtime\whisper.stderr.log.'
