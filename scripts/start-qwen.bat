@echo off
cd /d "%~dp0\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-qwen.ps1"
if errorlevel 1 (
    echo [ERROR] Could not start Qwen. See the message above.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-whisper.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
".venv\Scripts\python.exe" "%~dp0configure-qwen.py"
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-companion.ps1"
if errorlevel 1 (
    pause
    exit /b 1
)
echo [OK] Open http://localhost:8000. Chat, offline microphone, and local TTS are ready.
pause
