# HER Project Structure

This document describes the complete directory structure of the HER project.

## Root Directory

```
her/
├── .gitignore                    # Git ignore rules (secrets, runtime data)
├── .env                          # Environment variables (NOT committed)
├── .env.example                  # Environment variables template (committed)
├── README.md                     # Project overview and quick start
├── .venv/                        # Python virtual environment (NOT committed)
│
├── backend/                      # FastAPI backend application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── api/                 # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── health.py        # Health check endpoints
│   │   │   ├── system.py        # System status endpoints
│   │   │   └── settings.py      # Settings endpoints
│   │   ├── core/                # Core functionality
│   │   │   ├── __init__.py
│   │   │   ├── config.py        # Configuration and settings
│   │   │   └── database.py      # Database connection and models
│   │   └── models/              # Database models
│   │       ├── __init__.py
│   │       ├── app_meta.py      # Application metadata
│   │       ├── system_events.py # System event logging
│   │       └── local_settings.py # Local configuration storage
│   ├── tests/                   # Backend tests
│   │   ├── __init__.py
│   │   ├── test_health.py       # Health endpoint tests
│   │   └── test_database_bootstrap.py # Database tests
│   ├── pytest.ini               # pytest configuration
│   └── requirements.txt          # Python dependencies
│
├── frontend/                     # Next.js frontend application
│   ├── src/
│   │   ├── app/                 # Next.js app directory
│   │   │   ├── page.tsx         # Dashboard page
│   │   │   ├── layout.tsx       # Root layout
│   │   │   ├── autoquant/       # AutoQuant runs page
│   │   │   ├── strategy-lab/    # Strategy lab page
│   │   │   ├── strategy-editor/ # Strategy editor page
│   │   │   ├── optimizer/       # Optimizer page
│   │   │   ├── results/         # Results viewer page
│   │   │   ├── runs/            # Run history page
│   │   │   ├── settings/        # Settings page
│   │   │   └── ai-assistant/    # AI assistant page
│   │   ├── components/          # React components
│   │   │   ├── AppShell.tsx     # Main app shell with sidebar/topbar
│   │   │   ├── Sidebar.tsx      # Navigation sidebar
│   │   │   ├── TopBar.tsx       # Top status bar
│   │   │   ├── SystemHealthCard.tsx # Health status card
│   │   │   ├── StatusBadge.tsx  # Status indicator badge
│   │   │   └── EmptyState.tsx   # Empty state placeholder
│   │   └── lib/                 # Frontend utilities
│   │       ├── api.ts           # API client functions
│   │       └── types.ts         # TypeScript type definitions
│   ├── public/                  # Static assets
│   ├── package.json             # Node.js dependencies
│   ├── tsconfig.json            # TypeScript configuration
│   ├── next.config.js           # Next.js configuration
│   ├── tailwind.config.ts       # Tailwind CSS configuration
│   └── .env.local               # Frontend environment (NOT committed)
│
├── data/                         # Data directory
│   └── her.db                   # SQLite database (NOT committed)
│
├── freqtrade_workspace/          # Freqtrade workspace
│   ├── user_data/               # Freqtrade user data directory
│   │   ├── strategies/          # Strategy files (.py)
│   │   │   └── README.md        # Strategies documentation
│   │   ├── data/                # Market data (NOT committed)
│   │   │   └── README.md        # Data directory documentation
│   │   ├── backtest_results/    # Backtest results (NOT committed)
│   │   │   └── README.md        # Backtest results documentation
│   │   ├── hyperopt_results/    # Hyperopt results (NOT committed)
│   │   │   └── README.md        # Hyperopt results documentation
│   │   ├── hyperopts/           # Hyperopt scripts
│   │   │   └── README.md        # Hyperopts documentation
│   │   ├── plot/                # Plot files (NOT committed)
│   │   │   └── README.md        # Plot directory documentation
│   │   └── logs/                # Freqtrade logs (NOT committed)
│   │       └── README.md        # Logs directory documentation
│   └── config/                  # Freqtrade configuration files
│       ├── config.json          # Base Freqtrade config
│       └── config.generated.json # Generated config (HER-managed)
│
├── artifacts/                    # Run artifacts and outputs (NOT committed)
│   └── runs/                    # Individual run artifacts
│
├── exports/                      # Exported data and reports (NOT committed)
│
├── backups/                      # Database backups (NOT committed)
│
├── logs/                         # Application logs (NOT committed)
│
├── scripts/                      # Utility and development scripts
│   ├── dev.sh                   # Development instructions
│   ├── dev-backend.sh           # Start backend server
│   ├── dev-frontend.sh          # Start frontend server
│   ├── init-db.py               # Initialize database
│   ├── check-system.py          # System health check
│   ├── test-freqtrade.py        # Freqtrade integration check
│   ├── test-ollama.py           # Ollama integration check
│   ├── test-discord-env.py      # Discord integration check
│   └── print-env-status.py      # Environment status display
│
└── docs/                         # Documentation
    ├── PRODUCT_CHARTER.md       # Product identity and mission
    ├── TRADING_DEFINITIONS.md   # Trading evaluation rules
    ├── AI_PERMISSIONS.md        # AI roles and permissions
    ├── RUN_LIFECYCLE.md        # Complete run lifecycle
    ├── UI_BLUEPRINT.md         # UI/UX specifications
    ├── QUALITY_RULES.md        # Quality standards
    ├── PARTS_ROADMAP.md        # Development roadmap
    ├── FOUNDATION_INDEX.md     # Foundation document index
    ├── PART_02_SETUP_NOTES.md  # Part 02 setup documentation
    ├── PART_02_COMPLETION_REPORT.md # Part 02 completion report
    ├── LOCAL_INTEGRATION_CHECKS.md # Integration check documentation
    ├── PROJECT_STRUCTURE.md    # This file
    └── ENVIRONMENT_AND_SECRETS.md # Environment and secrets guide
```

## Directory Purposes

### Backend (`backend/`)
FastAPI application serving REST API for HER. Handles database operations, system status, and integration with external services.

### Frontend (`frontend/`)
Next.js React application providing the user interface. Displays system status, run results, and configuration options.

### Data (`data/`)
Contains SQLite database for storing application state, settings, and system events.

### Freqtrade Workspace (`freqtrade_workspace/`)
Workspace for Freqtrade trading engine integration. Contains strategies, data, configurations, and results.

### Artifacts (`artifacts/`)
Stores generated artifacts from AutoQuant runs, including strategy files, backtest results, and analysis reports.

### Exports (`exports/`)
Contains exported data and reports generated by HER for external use.

### Backups (`backups/`)
Database backups and configuration snapshots.

### Logs (`logs/`)
Application logs for debugging and monitoring.

### Scripts (`scripts/`)
Utility scripts for development, testing, and system maintenance.

### Documentation (`docs/`)
Complete project documentation including foundation documents, setup guides, and reference materials.

## File Naming Conventions

- **Python files:** `snake_case.py`
- **TypeScript/React files:** `PascalCase.tsx` or `PascalCase.ts`
- **Documentation:** `UPPER_CASE.md`
- **Configuration:** `kebab-case.json` or `kebab-case.yml`

## Security Considerations

- `.env` file is NEVER committed to Git
- Database files in `data/` are ignored
- Freqtrade data and results are ignored
- Logs and artifacts are ignored
- All sensitive data uses Pydantic SecretStr in backend
- See `.gitignore` for complete list of ignored files
