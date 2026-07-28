#!/usr/bin/env bash

echo "========================================================"
echo "                IWantYT Downloader"
echo "========================================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python 3 is not installed. Please install Python 3.10+."
    exit 1
fi

# Create virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment (.venv)..."
    python3 -m venv .venv
    echo "[SUCCESS] Virtual environment created."
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "[INFO] Checking and installing dependencies..."
pip install -r requirements.txt --quiet
echo "[SUCCESS] Dependencies are ready."

# Open browser
if command -v open &> /dev/null; then
    open http://127.0.0.1:8000
elif command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000
fi

echo "[INFO] Starting FastAPI server on http://127.0.0.1:8000..."
python main.py
