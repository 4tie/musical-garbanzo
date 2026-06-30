"""
API router for Strategy and Strategy Version operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.strategies import (
    StrategyRepository,
    StrategyNotFoundError,
    StrategyVersionNotFoundError,
)
from app.schemas.strategies import (
    StrategyCreate,
    StrategyUpdate,
    StrategyRead,
    StrategyListItem,
    StrategyVersionCreate,
    StrategyVersionRead,
    StrategyVersionListItem,
)

router = APIRouter(tags=["Strategies"])
strategy_repo = StrategyRepository()


@router.get("/strategies", response_model=list[StrategyListItem])
def list_strategies(
    status: str = None,
    source_type: str = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List strategies with optional filters.
    
    Supports filtering by status and source_type.
    """
    strategies = strategy_repo.list_strategies(
        status=status,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )
    return strategies


@router.post("/strategies", response_model=StrategyRead, status_code=201)
def create_strategy(data: StrategyCreate):
    """
    Create a new strategy.
    
    This creates a strategy record in the database.
    It does not generate strategy code or write files to disk.
    """
    try:
        strategy = strategy_repo.create_strategy(data)
        return strategy
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/strategies/{strategy_id}", response_model=StrategyRead)
def get_strategy(strategy_id: str):
    """
    Get a specific strategy by ID.
    
    Returns detailed information about the strategy.
    """
    strategy = strategy_repo.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    return strategy


@router.patch("/strategies/{strategy_id}", response_model=StrategyRead)
def update_strategy(strategy_id: str, data: StrategyUpdate):
    """
    Update a strategy.
    
    Updates specific fields of a strategy.
    Does not modify strategy files on disk.
    """
    try:
        strategy = strategy_repo.update_strategy(strategy_id, data)
        return strategy
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/strategies/{strategy_id}/archive", response_model=StrategyRead)
def archive_strategy(strategy_id: str):
    """
    Archive a strategy.
    
    Sets the strategy status to 'archived'.
    """
    try:
        strategy = strategy_repo.archive_strategy(strategy_id)
        return strategy
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")


@router.get("/strategies/{strategy_id}/versions", response_model=list[StrategyVersionListItem])
def list_versions(strategy_id: str):
    """
    List all versions for a strategy.
    
    Returns versions in descending order by version number.
    The current version is marked with is_current = True.
    """
    # Verify strategy exists
    strategy = strategy_repo.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    versions = strategy_repo.list_versions(strategy_id)
    return versions


@router.post("/strategies/{strategy_id}/versions", response_model=StrategyVersionRead, status_code=201)
def create_version(strategy_id: str, data: StrategyVersionCreate):
    """
    Create a new strategy version.
    
    Creates a version record. If version_number is not provided,
    it will be auto-incremented from the latest version.
    This does not write strategy files to disk.
    """
    # Override strategy_id to match URL parameter
    if data is None:
        data = StrategyVersionCreate()
    data.strategy_id = strategy_id
    
    try:
        version = strategy_repo.create_version(data)
        return version
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")


@router.get("/strategies/{strategy_id}/current-version", response_model=StrategyVersionRead)
def get_current_version(strategy_id: str):
    """
    Get the current version for a strategy.
    
    Returns the version marked as current for this strategy.
    """
    # Verify strategy exists
    strategy = strategy_repo.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    version = strategy_repo.get_current_version(strategy_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"No current version set for strategy {strategy_id}")
    
    return version


@router.post("/strategies/{strategy_id}/current-version/{version_id}", response_model=StrategyRead)
def set_current_version(strategy_id: str, version_id: str):
    """
    Set the current version for a strategy.
    
    Marks the specified version as the current version for the strategy.
    """
    try:
        strategy = strategy_repo.set_current_version(strategy_id, version_id)
        return strategy
    except StrategyNotFoundError:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    except StrategyVersionNotFoundError:
        raise HTTPException(status_code=404, detail=f"Version {version_id} not found")
