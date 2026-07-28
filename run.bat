@echo off
setlocal enabledelayedexpansion
title IWantYT Local Downloader
cd /d "%~dp0"

echo ========================================================
echo                 IWantYT Downloader
echo ========================================================
echo.

REM Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found on your system.
    echo Please install Python 3.10 or higher from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Create virtual environment if missing
if not exist ".venv" (
    echo [INFO] Creating virtual environment .venv
    python -m venv .venv
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
    echo.
)

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [WARNING] Virtual environment activation script not found. Using system Python.
)

REM Free port 8000 if occupied by a previous server instance
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

REM Install dependencies
echo [INFO] Checking Python dependencies
pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Pip install had warnings or errors. Attempting to start server anyway.
)
echo [SUCCESS] Dependencies ready.
echo.

REM Start FastAPI server
echo [INFO] Starting IWantYT server at http://127.0.0.1:8000
echo [INFO] Press Ctrl+C in this window to stop the server.
echo ========================================================
echo.

python main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Python server exited with error code %ERRORLEVEL%.
    pause
)
