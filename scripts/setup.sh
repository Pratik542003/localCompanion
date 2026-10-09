#!/usr/bin/env bash
set -e

echo "============================================"
echo "  Local Companion - Setup Script (Linux)"
echo "============================================"
echo

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python3 is not installed."
    echo "Install it with: sudo apt install python3 python3-venv python3-pip"
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo "[OK] Found $PYVER"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
echo "[INFO] Project directory: $(pwd)"

# Create virtual environment
if [ ! -f ".venv/bin/python" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv .venv
    echo "[OK] Virtual environment created."
else
    echo "[OK] Virtual environment already exists."
fi

# Install dependencies
echo "[INFO] Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1
pip install -e .
echo "[OK] Dependencies installed."

# Create .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[OK] Created .env from .env.example"
else
    echo "[OK] .env already exists."
fi

# Create data directory
mkdir -p data
echo "[OK] Data directory ready."

echo
echo "============================================"
echo "  Setup complete!"
echo
echo "  To start the application:"
echo "    source .venv/bin/activate"
echo "    python -m uvicorn app.main:app --reload"
echo
echo "  Then open http://localhost:8000"
echo "============================================"
