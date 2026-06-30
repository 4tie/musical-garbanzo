"""
System status and health endpoints.
"""
from fastapi import APIRouter, Query

from app.core.config import settings
from app.services.system_service import (
    get_system_status,
    get_recent_events,
    get_public_settings_status,
)
from app.schemas.common import HealthStatus

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "backend": "healthy",
    }


@router.get("/api/system/status")
async def system_status():
    """Public-safe system status endpoint."""
    return get_system_status()


@router.get("/api/settings/public")
async def public_settings():
    """Public-safe settings endpoint (no secrets)."""
    return get_public_settings_status()


@router.get("/api/system/events")
async def system_events(limit: int = Query(50, ge=1, le=100)):
    """Get recent system events."""
    return get_recent_events(limit)
