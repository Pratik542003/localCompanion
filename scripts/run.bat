@echo off
echo ============================================
echo   Local Companion - Starting...
echo ============================================

cd /d "%~dp0\.."

:: Check if venv exists
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

:: Check if dependencies are installed
.venv\Scripts\python.exe -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependencies not installed.
    echo Please run setup.bat first.
    pause
    exit /b 1
)

:: Create .env if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] Created .env from .env.example
    )
)

:: Create data directory
if not exist "data" mkdir data

:: Clear Python cache to ensure fresh code
for /d /r "app" %%d in (__pycache__) do if exist "%%d" rd /s /q "%%d" >nul 2>&1

echo.
echo [INFO] Starting Local Companion on http://localhost:8000
echo [INFO] Press Ctrl+C to stop.
echo.

call .venv\Scripts\activate.bat
set PYTHONDONTWRITEBYTECODE=1
python -B -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
