"""
HER Backend Main Entry Point
FastAPI application for local trading strategy validation
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.routers.system import router as system_router
from app.api.v1.routers.runs import router as runs_router
from app.api.v1.routers.run_stages import router as run_stages_router
from app.api.v1.routers.strategies import router as strategies_router
from app.api.v1.routers.strategy_workspace import router as strategy_workspace_router
from app.api.v1.routers.artifacts import router as artifacts_router
from app.api.v1.routers.metrics import router as metrics_router
from app.api.v1.routers.logs import router as logs_router
from app.api.v1.routers.retry_history import router as retry_history_router
from app.api.v1.routers.audit_logs import router as audit_logs_router
from app.api.v1.routers.freqtrade import router as freqtrade_router
from app.api.v1.routers.results import router as results_router
from app.api.v1.routers.decisions import router as decisions_router
from app.api.v1.routers.baseline import router as baseline_router
from app.api.v1.routers.optimization import router as optimization_router
from app.api.v1.routers.validation import router as validation_router
from app.core.config import settings
from app.services.system_service import initialize_backend


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    initialize_backend()
    yield
    # Shutdown (if needed)
    pass


app = FastAPI(
    title="HER API",
    description="Local-only trading strategy validation system",
    version="0.3.0",
    lifespan=lifespan,
)

# Configure CORS for local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(system_router)
app.include_router(strategy_workspace_router, prefix="/api")


def include_part_03_routers(prefix: str) -> None:
    """Mount Part 03 API routers under a shared prefix."""
    app.include_router(runs_router, prefix=prefix)
    app.include_router(run_stages_router, prefix=prefix)
    app.include_router(strategies_router, prefix=prefix)
    app.include_router(artifacts_router, prefix=prefix)
    app.include_router(metrics_router, prefix=prefix)
    app.include_router(logs_router, prefix=prefix)
    app.include_router(retry_history_router, prefix=prefix)
    app.include_router(audit_logs_router, prefix=prefix)
    app.include_router(freqtrade_router, prefix=f"{prefix}/freqtrade")
    app.include_router(results_router, prefix=prefix)
    app.include_router(decisions_router, prefix=prefix)
    app.include_router(baseline_router, prefix=prefix)
    app.include_router(optimization_router, prefix=prefix)
    app.include_router(validation_router, prefix=prefix)


include_part_03_routers(prefix="/api")
include_part_03_routers(prefix="/api/v1")
register_exception_handlers(app)


@app.get("/")
async def root():
    return {"message": "HER Backend API - Local Trading Strategy Validation System"}
