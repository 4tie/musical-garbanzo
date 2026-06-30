"""
Freqtrade API endpoints for HER.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["Freqtrade"])

from app.core.config import settings
from app.services.freqtrade_detection import FreqtradeDetectionService
from app.services.freqtrade_workspace import FreqtradeWorkspaceService
from app.services.freqtrade_strategy_service import FreqtradeStrategyService
from app.services.freqtrade_data_service import FreqtradeDataService
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner
from app.schemas.freqtrade import FreqtradeStatus, FreqtradeVersion, FreqtradeWorkspaceStatus
from app.schemas.freqtrade_strategy import FreqtradeStrategyStatus
from app.schemas.freqtrade_strategy import FreqtradeStrategyFile
from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
from app.schemas.freqtrade_data import (
    FreqtradeDataCheckRequest,
    FreqtradeDataCheckResult,
    FreqtradeDataDownloadRequest,
    FreqtradeDataDownloadResult,
)
from app.schemas.freqtrade_backtest import (
    FreqtradeBacktestRequest,
    FreqtradeBacktestResult,
)
from app.repositories.logs import RunLogRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.artifacts import ArtifactRepository

router = APIRouter(tags=["Freqtrade"])


# Request/Response models for API
class StatusResponse(BaseModel):
    """Freqtrade status response."""
    configured: bool
    executable_available: bool
    version: Optional[str] = None
    workspace_valid: bool = False
    allowed_commands: list[str] = []
    forbidden_commands: list[str] = []
    real_smoke_enabled: bool = False
    warnings: list[str] = []
    error: Optional[str] = None


class VersionResponse(BaseModel):
    """Freqtrade version response."""
    version: Optional[str] = None
    available: bool = False
    error: Optional[str] = None


class WorkspaceResponse(BaseModel):
    """Freqtrade workspace response."""
    valid: bool
    user_data_dir: str
    config_dir: str
    missing_dirs: list[str] = []
    created_dirs: list[str] = []
    user_action_required: Optional[str] = None
    error: Optional[str] = None


class StrategiesListResponse(BaseModel):
    """Strategies list response."""
    strategies: list[FreqtradeStrategyFile] = []
    source: str = "local"
    error: Optional[str] = None


class StrategyDetailResponse(BaseModel):
    """Strategy detail response."""
    strategy: Optional[FreqtradeStrategyStatus] = None
    error: Optional[str] = None


class DataOverviewResponse(BaseModel):
    """Data overview response."""
    data_dir: str
    exists: bool
    pairs_count: int = 0
    error: Optional[str] = None


class ConfigBacktestRequest(BaseModel):
    """Request for generating backtest config."""
    run_id: Optional[str] = None
    config_path: Optional[str] = None
    strategy_name: str
    timeframe: str
    pairs: Optional[list[str]] = None
    timerange: Optional[str] = None
    stake_currency: Optional[str] = None
    stake_amount: Optional[float] = None
    dry_run: bool = True


class ConfigBacktestResponse(BaseModel):
    """Response for backtest config generation."""
    success: bool
    config_path: Optional[str] = None
    artifact_id: Optional[str] = None
    error: Optional[str] = None


# Initialize services
detector = FreqtradeDetectionService()
workspace_service = FreqtradeWorkspaceService()
strategy_service = FreqtradeStrategyService()
data_service = FreqtradeDataService()
config_generator = FreqtradeConfigGenerator()
backtest_runner = FreqtradeBacktestRunner()
log_repository = RunLogRepository()
audit_repository = AuditLogRepository()
artifact_repository = ArtifactRepository()


@router.get("/status", response_model=StatusResponse)
async def get_freqtrade_status():
    """Get Freqtrade status and configuration."""
    try:
        status = detector.get_status()
        
        # Get allowed/forbidden commands from command runner
        from app.services.freqtrade_command_runner import FreqtradeCommandRunner
        command_runner = FreqtradeCommandRunner()
        
        return StatusResponse(
            configured=status.configured,
            executable_available=status.executable_available,
            version=status.version,
            workspace_valid=status.workspace_valid if status.workspace else False,
            allowed_commands=command_runner.ALLOWED_COMMANDS,
            forbidden_commands=command_runner.FORBIDDEN_COMMANDS,
            real_smoke_enabled=settings.FREQTRADE_REAL_SMOKE_ENABLED,
            warnings=[],
            error=status.error,
        )
    except Exception as e:
        return StatusResponse(
            configured=False,
            executable_available=False,
            error=str(e),
        )


@router.get("/version", response_model=VersionResponse)
async def get_freqtrade_version():
    """Get Freqtrade version."""
    try:
        version_info = detector.get_version()
        return VersionResponse(
            version=version_info.version,
            available=version_info.available,
            error=version_info.error,
        )
    except Exception as e:
        return VersionResponse(
            available=False,
            error=str(e),
        )


@router.get("/workspace", response_model=WorkspaceResponse)
async def get_freqtrade_workspace():
    """Get Freqtrade workspace status."""
    try:
        workspace = workspace_service.validate_workspace()
        return WorkspaceResponse(
            valid=workspace.valid,
            user_data_dir=workspace.user_data_dir,
            config_dir=workspace.config_dir,
            missing_dirs=workspace.missing_dirs,
            created_dirs=workspace.created_dirs,
            user_action_required=workspace.user_action_required,
            error=None,
        )
    except Exception as e:
        return WorkspaceResponse(
            valid=False,
            user_data_dir=str(settings.freqtrade_user_data_dir_path),
            config_dir=str(settings.freqtrade_config_dir_path),
            error=str(e),
        )


@router.get("/strategies", response_model=StrategiesListResponse)
async def list_strategies():
    """List available strategies."""
    try:
        result = strategy_service.list_strategy_files()
        return StrategiesListResponse(
            strategies=result.strategies,
            source=result.source,
            error="; ".join(result.errors) if result.errors else None,
        )
    except Exception as e:
        return StrategiesListResponse(
            strategies=[],
            source="local",
            error=str(e),
        )


@router.get("/strategies/{strategy_name}", response_model=StrategyDetailResponse)
async def get_strategy(strategy_name: str):
    """Get specific strategy status."""
    try:
        status = strategy_service.get_strategy_status(strategy_name)
        return StrategyDetailResponse(
            strategy=status,
            error=None,
        )
    except Exception as e:
        return StrategyDetailResponse(
            strategy=None,
            error=str(e),
        )


@router.get("/data", response_model=DataOverviewResponse)
async def get_data_overview(
    exchange: Optional[str] = None,
    trading_mode: Optional[str] = None,
    timeframe: Optional[str] = None,
):
    """Get data directory overview."""
    try:
        data_dir = data_service.get_data_dir()
        exists = data_dir.exists()
        
        pairs_count = 0
        if exists:
            # Count pair directories
            pairs_count = len([d for d in data_dir.iterdir() if d.is_dir()])
        
        return DataOverviewResponse(
            data_dir=str(data_dir),
            exists=exists,
            pairs_count=pairs_count,
            error=None,
        )
    except Exception as e:
        return DataOverviewResponse(
            data_dir=str(data_service.get_data_dir()),
            exists=False,
            pairs_count=0,
            error=str(e),
        )


@router.post("/config/backtest", response_model=ConfigBacktestResponse)
async def generate_backtest_config(request: ConfigBacktestRequest):
    """Generate safe backtest config."""
    try:
        config_request = FreqtradeBacktestConfigRequest(
            run_id=request.run_id or "api-config-preview",
            strategy_name=request.strategy_name,
            timeframe=request.timeframe,
            pairs=request.pairs or [],
            timerange=request.timerange,
            stake_currency=request.stake_currency or settings.FREQTRADE_DEFAULT_STAKE_CURRENCY,
            stake_amount=str(request.stake_amount) if request.stake_amount is not None else "unlimited",
        )
        result = config_generator.write_backtest_config(config_request)
        
        return ConfigBacktestResponse(
            success=result.success,
            config_path=result.config_path,
            artifact_id=result.artifact_id if result.success else None,
            error=result.error,
        )
    except Exception as e:
        return ConfigBacktestResponse(
            success=False,
            error=str(e),
        )


@router.post("/data/check", response_model=FreqtradeDataCheckResult)
async def check_data_availability(request: FreqtradeDataCheckRequest):
    """Check data availability."""
    try:
        result = data_service.check_data(request)
        return result
    except Exception as e:
        return FreqtradeDataCheckResult(
            run_id=request.run_id,
            exchange=request.exchange,
            trading_mode=request.trading_mode,
            pairs=[],
            source="error",
            freqtrade_visible=False,
            errors=[str(e)],
        )


@router.post("/data/download", response_model=FreqtradeDataDownloadResult)
async def download_data(request: FreqtradeDataDownloadRequest):
    """Download data (requires user confirmation)."""
    try:
        result = data_service.download_data(request)
        return result
    except (ValueError, HTTPException) as e:
        # Validation errors (e.g., user_confirmed=false)
        # Re-raise HTTPException as-is, convert ValueError to HTTPException
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return FreqtradeDataDownloadResult(
            run_id=request.run_id,
            exchange=request.exchange,
            trading_mode=request.trading_mode,
            pairs=request.pairs,
            timeframes=request.timeframes,
            success=False,
            blocked=False,
            error=str(e),
            errors=[str(e)],
        )


@router.post("/backtest", response_model=FreqtradeBacktestResult)
async def run_backtest(request: FreqtradeBacktestRequest):
    """Run Freqtrade backtest (requires user confirmation)."""
    try:
        result = backtest_runner.run_backtest(request)
        return result
    except (ValueError, HTTPException) as e:
        # Validation errors (e.g., user_confirmed=false)
        # Re-raise HTTPException as-is, convert ValueError to HTTPException
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return FreqtradeBacktestResult(
            run_id=request.run_id,
            success=False,
            blocked=False,
            error=str(e),
            errors=[str(e)],
        )
