#!/usr/bin/env bash
set -e

echo "============================================"
echo "  Local Companion - Starting..."
echo "============================================"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Check venv
if [ ! -f ".venv/bin/python" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Please run setup.sh first."
    exit 1
fi

# Check dependencies
if ! .venv/bin/python -c "import fastapi" 2>/dev/null; then
    echo "[ERROR] Dependencies not installed."
    echo "Please run setup.sh first."
    exit 1
fi

# Create .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[OK] Created .env from .env.example"
fi

mkdir -p data

echo
echo "[INFO] Starting Local Companion on http://localhost:8000"
echo "[INFO] Press Ctrl+C to stop."
echo

source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
