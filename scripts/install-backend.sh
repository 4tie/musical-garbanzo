#!/usr/bin/env bash
# install-backend.sh — Deterministic backend dependency install for HER.
#
# Problem: freqtrade's transitive dependencies pull in a newer FastAPI version
# (>=0.115) that is incompatible with HER's pinned fastapi==0.104.1 + pydantic==2.5.0.
# Running a plain `pip install -r requirements.txt` can silently pick the wrong version.
#
# This script installs in two stages to guarantee the correct pinned versions win:
#   Stage 1: Install freqtrade and all its deps (may install newer FastAPI).
#   Stage 2: Re-install the HER-pinned versions, overriding any conflict.
#
# Usage:
#   bash scripts/install-backend.sh            # from project root
#   bash scripts/install-backend.sh --quiet    # suppress pip output

set -e

QUIET="${1:-}"
PIP_FLAGS=""
if [[ "$QUIET" == "--quiet" ]]; then
  PIP_FLAGS="--quiet"
fi

echo "==> Stage 1: Installing all backend dependencies (including freqtrade)..."
pip install -r backend/requirements.txt $PIP_FLAGS

echo "==> Stage 2: Pinning HER-required versions (fastapi, pydantic, starlette)..."
pip install \
  "fastapi==0.104.1" \
  "pydantic==2.5.0" \
  "pydantic-settings==2.1.0" \
  "starlette==0.27.0" \
  --force-reinstall $PIP_FLAGS

echo ""
echo "✓ Backend dependencies installed."
echo "  fastapi:          $(pip show fastapi 2>/dev/null | grep Version | awk '{print $2}')"
echo "  pydantic:         $(pip show pydantic 2>/dev/null | grep Version | awk '{print $2}')"
echo "  freqtrade:        $(pip show freqtrade 2>/dev/null | grep Version | awk '{print $2}')"
echo ""
echo "Run 'cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload' to start."
