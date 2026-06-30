#!/bin/bash
# HER Local Development Script
# Prints instructions and optionally starts backend and frontend

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "HER Local Development Environment"
echo "=========================================="
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠ Virtual environment not found"
    echo "  Create it with: python3 -m venv .venv"
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠ .env file not found"
    echo "  Create it from .env.example: cp .env.example .env"
    echo ""
fi

echo "=========================================="
echo "Development Options:"
echo "=========================================="
echo ""
echo "1. Start Backend Only:"
echo "   source .venv/bin/activate"
echo "   export PYTHONPATH=$PROJECT_ROOT/backend"
echo "   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
echo ""
echo "2. Start Frontend Only:"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "3. Start Both (Separate Terminals):"
echo "   Terminal 1 (Backend):"
echo "   source .venv/bin/activate"
echo "   export PYTHONPATH=$PROJECT_ROOT/backend"
echo "   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
echo ""
echo "   Terminal 2 (Frontend):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Use Convenience Scripts:"
echo "   ./scripts/dev-backend.sh    # Start backend"
echo "   ./scripts/dev-frontend.sh   # Start frontend"
echo ""
echo "=========================================="
echo "Integration Check Scripts:"
echo "=========================================="
echo ""
echo "Check Freqtrade:"
echo "  python scripts/test-freqtrade.py"
echo ""
echo "Check Ollama:"
echo "  python scripts/test-ollama.py"
echo ""
echo "Check Discord:"
echo "  python scripts/test-discord-env.py"
echo "  python scripts/test-discord-env.py --send-test  # Send test message"
echo ""
echo "Check System:"
echo "  python scripts/check-system.py"
echo ""
echo "=========================================="
echo "URLs:"
echo "=========================================="
echo ""
echo "Backend API: http://127.0.0.1:8000"
echo "Frontend:    http://127.0.0.1:3000"
echo "API Docs:    http://127.0.0.1:8000/docs"
echo ""
echo "=========================================="
