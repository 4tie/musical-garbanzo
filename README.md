# HER - AutoQuant Strategy Lab

## Project Description
HER is a complete local-only trading strategy validation application built from scratch for one private user. It serves as a serious local strategy lab that helps create, test, improve, validate, and export Freqtrade-compatible trading strategies.

HER is a validation engine, not a guaranteed profitable strategy generator. It helps search for profitable candidates, but every claim must be backed by tests, metrics, robustness checks, and clear decision logic.

## Intended Stack
- Frontend: Next.js + React + TypeScript + Tailwind CSS
- Backend: FastAPI + Python
- Database: SQLite
- AI: Ollama/local LLM integration
- Trading engine: Freqtrade
- Notifications/chat integration: Discord bot
- Secrets: `.env` file only, never hardcoded tokens
- Artifacts: local filesystem folders
- Export: `.py`, `.json`, reports, and optional config files

## Project Notes
This is a new local-only project built from scratch. The application runs locally on the user's own machine with all artifacts stored locally in filesystem folders. No cloud deployment, Docker, Kubernetes, PostgreSQL, SaaS, or public hosting assumptions are introduced.

## Core Operating Principle
**AI suggests. Backend validates. Freqtrade tests. HER decides.**

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm

### Backend Setup
```bash
# Create virtual environment (already created)
python3 -m venv .venv

# Install dependencies
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run backend server
bash scripts/dev-backend.sh
# Or manually:
export PYTHONPATH=/home/mohs/Desktop/her/backend
.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL: http://127.0.0.1:8000

### Frontend Setup
```bash
cd frontend
npm install

# Run frontend server
cd ..
bash scripts/dev-frontend.sh
# Or manually:
cd frontend
npm run dev
```

Frontend URL: http://127.0.0.1:3000

### Running Tests
```bash
# Backend tests
source .venv/bin/activate
pytest backend/tests

# Frontend lint
cd frontend
npm run lint
```

## Export Format
When a strategy passes validation, HER exports:
- Freqtrade-ready `.py` strategy file
- Matching `.json` parameter file
- Comprehensive validation reports

## Important Disclaimer
HER does not guarantee profitable trading strategies. It is a validation engine that helps search for profitable candidates through rigorous testing, but all strategies must be evaluated with appropriate risk management and user judgment.
