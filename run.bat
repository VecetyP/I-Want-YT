@echo off
title IWantYT — Local YouTube Downloader
cd /d "%~dp0"

echo ========================================================
echo                 IWantYT Downloader
echo ========================================================
echo.

:: Ensure Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo.
    pause
    exit /b
)

:: Create virtual environment if missing
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
    echo [SUCCESS] Virtual environment created.
    echo.
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Install dependencies
echo [INFO] Checking dependencies...
pip install -r requirements.txt --quiet
echo [SUCCESS] Dependencies ready.
echo.

:: Launch browser & start server
echo [INFO] Opening web browser at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"

echo [INFO] Starting FastAPI server...
echo ========================================================
python main.py

pause
