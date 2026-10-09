@echo off
echo ============================================
echo   Local Companion - Setup Script (Windows)
echo ============================================
echo.

:: Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.11 or newer from https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Found Python %PYVER%

:: Navigate to project root
cd /d "%~dp0\.."
echo [INFO] Project directory: %cd%

:: Create virtual environment if it doesn't exist
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate and install dependencies
echo [INFO] Installing dependencies...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -e . 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: Create .env from example if it doesn't exist
if not exist ".env" (
    copy .env.example .env >nul
    echo [OK] Created .env from .env.example
) else (
    echo [OK] .env already exists.
)

:: Create data directory
if not exist "data" mkdir data
echo [OK] Data directory ready.

echo.
echo ============================================
echo   Setup complete!
echo.
echo   To start the application:
echo     .venv\Scripts\activate.bat
echo     python -m uvicorn app.main:app --reload
echo.
echo   Then open http://localhost:8000
echo ============================================
pause
