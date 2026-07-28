@echo off
title IWantYT — Local YouTube Downloader Launcher
cls

echo ========================================================
echo                 IWantYT Downloader
echo ========================================================
echo.

:: Check for Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo.
    pause
    exit /b
)

:: Check if .venv virtual environment exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
    echo [SUCCESS] Virtual environment created.
    echo.
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Install / Update dependencies
echo [INFO] Checking and installing dependencies...
pip install -r requirements.txt --quiet
echo [SUCCESS] Dependencies are ready.
echo.

:: Open default browser after 2 seconds
echo [INFO] Opening web browser at http://127.0.0.1:8000 ...
timeout /t 2 >nul
start http://127.0.0.1:8000

:: Start FastAPI Server
echo [INFO] Starting FastAPI server on http://127.0.0.1:8000 (Press Ctrl+C to stop)...
echo ========================================================
python main.py

pause
