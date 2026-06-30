"""
API router for Artifacts operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifacts import ArtifactCreate, ArtifactRead, ArtifactListItem

router = APIRouter(tags=["Artifacts"])
artifact_repo = ArtifactRepository()


@router.get("/artifacts", response_model=list[ArtifactListItem])
def list_artifacts(
    run_id: str = None,
    strategy_id: str = None,
    artifact_type: str = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List artifacts with optional filters.
    
    Supports filtering by run_id, strategy_id, and artifact_type.
    """
    artifacts = artifact_repo.list_artifacts(
        run_id=run_id,
        strategy_id=strategy_id,
        artifact_type=artifact_type,
        limit=limit,
        offset=offset,
    )
    return artifacts


@router.post("/artifacts", response_model=ArtifactRead, status_code=201)
def create_artifact(data: ArtifactCreate):
    """
    Create a new artifact.
    
    This creates an artifact record in the database.
    It does not read or download file content.
    """
    try:
        artifact = artifact_repo.create_artifact(data)
        return artifact
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/artifacts/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: str):
    """
    Get a specific artifact by ID.
    
    Returns detailed information about the artifact.
    """
    artifact = artifact_repo.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")
    return artifact


@router.get("/runs/{run_id}/artifacts", response_model=list[ArtifactListItem])
def list_run_artifacts(run_id: str):
    """
    List all artifacts for a run.
    
    Returns all artifacts associated with the specified run.
    """
    artifacts = artifact_repo.list_run_artifacts(run_id)
    return artifacts


@router.get("/strategies/{strategy_id}/artifacts", response_model=list[ArtifactListItem])
def list_strategy_artifacts(strategy_id: str):
    """
    List all artifacts for a strategy.
    
    Returns all artifacts associated with the specified strategy.
    """
    artifacts = artifact_repo.list_strategy_artifacts(strategy_id)
    return artifacts
