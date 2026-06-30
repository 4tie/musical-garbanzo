"""
Repository for Artifacts operations.
"""
from pathlib import Path
from typing import Optional, List

from app.core.constants import ARTIFACT_TYPES
from app.core.config import settings
from app.db.sqlite import fetch_one, fetch_all, transaction
from app.repositories.base import BaseRepository
from app.schemas.artifacts import ArtifactCreate


class ArtifactRepository(BaseRepository):
    """Repository for artifact data access operations."""
    
    def create_artifact(self, data: ArtifactCreate) -> dict:
        """
        Create a new artifact.
        
        Args:
            data: Artifact creation data
        
        Returns:
            Created artifact as dictionary
        
        Raises:
            ValueError: If artifact_type is invalid
        """
        self._require_allowed(data.artifact_type, ARTIFACT_TYPES, "artifact_type")
        
        artifact_id = self._uuid()
        now = self._now()
        file_path = self._project_relative_path(data.file_path)
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO artifacts (
                    id, run_id, strategy_id, artifact_type, path,
                    description, sha256, size_bytes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    data.run_id,
                    data.strategy_id,
                    data.artifact_type,
                    file_path,
                    data.description,
                    data.sha256,
                    data.size_bytes,
                    now,
                )
            )
        
        return self.get_artifact(artifact_id)
    
    def get_artifact(self, artifact_id: str) -> Optional[dict]:
        """
        Get an artifact by ID.
        
        Args:
            artifact_id: Artifact UUID
        
        Returns:
            Artifact as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM artifacts WHERE id = ?",
            (artifact_id,)
        )
        
        if row:
            return self._deserialize_artifact(self._row_to_dict(row))
        return None
    
    def list_artifacts(
        self,
        run_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """
        List artifacts with optional filters.
        
        Args:
            run_id: Filter by run ID
            strategy_id: Filter by strategy ID
            artifact_type: Filter by artifact type
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of artifact dictionaries
        """
        limit = self._normalize_limit(limit, default=50, max_value=500)
        
        query = "SELECT * FROM artifacts WHERE 1=1"
        params = []
        
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        
        if strategy_id:
            query += " AND strategy_id = ?"
            params.append(strategy_id)
        
        if artifact_type:
            query += " AND artifact_type = ?"
            params.append(artifact_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = fetch_all(query, tuple(params))
        return [self._deserialize_artifact(self._row_to_dict(row)) for row in rows]
    
    def list_run_artifacts(self, run_id: str) -> List[dict]:
        """
        List all artifacts for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            List of artifact dictionaries
        """
        return self.list_artifacts(run_id=run_id)
    
    def list_strategy_artifacts(self, strategy_id: str) -> List[dict]:
        """
        List all artifacts for a strategy.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            List of artifact dictionaries
        """
        return self.list_artifacts(strategy_id=strategy_id)

    def get_artifact_by_path(self, file_path: str, run_id: Optional[str] = None) -> Optional[dict]:
        """Get an artifact by stored file path, optionally scoped to a run."""
        stored_path = self._project_relative_path(file_path)
        query = "SELECT * FROM artifacts WHERE path = ?"
        params: list = [stored_path]

        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)

        query += " ORDER BY created_at DESC LIMIT 1"
        row = fetch_one(query, tuple(params))
        if row:
            return self._deserialize_artifact(self._row_to_dict(row))
        return None

    def create_or_update_artifact(self, data: ArtifactCreate) -> dict:
        """
        Create an artifact or update the existing row for the same run/path.

        This keeps generated parser artifacts idempotent while preserving the
        actual file content on disk.
        """
        existing = self.get_artifact_by_path(data.file_path, data.run_id)
        if not existing:
            return self.create_artifact(data)

        self._require_allowed(data.artifact_type, ARTIFACT_TYPES, "artifact_type")
        stored_path = self._project_relative_path(data.file_path)

        with transaction() as conn:
            conn.execute(
                """
                UPDATE artifacts
                SET artifact_type = ?, strategy_id = ?, description = ?,
                    sha256 = ?, size_bytes = ?
                WHERE id = ?
                """,
                (
                    data.artifact_type,
                    data.strategy_id,
                    data.description,
                    data.sha256,
                    data.size_bytes,
                    existing["id"],
                )
            )

        return self.get_artifact_by_path(stored_path, data.run_id)

    def _project_relative_path(self, file_path: str) -> str:
        """Store absolute paths under the project root as project-relative."""
        path = Path(file_path)
        if not path.is_absolute():
            return file_path

        try:
            return str(path.resolve(strict=False).relative_to(settings.project_root.resolve()))
        except ValueError:
            return file_path

    def _deserialize_artifact(self, row: dict) -> dict:
        """Expose artifact DB path as file_path for the API contract."""
        row["file_path"] = row.pop("path")
        return row
