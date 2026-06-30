"""
Repository for Strategy and Strategy Version operations.
"""
from typing import Optional, List, Any

from app.core.constants import (
    STRATEGY_SOURCE_TYPES,
    STRATEGY_STATUSES,
    STRATEGY_DIRECTIONS,
)
from app.db.sqlite import fetch_one, fetch_all, execute, transaction
from app.repositories.base import BaseRepository
from app.schemas.strategies import StrategyCreate, StrategyUpdate, StrategyVersionCreate


class StrategyNotFoundError(Exception):
    """Raised when a strategy is not found."""
    pass


class StrategyVersionNotFoundError(Exception):
    """Raised when a strategy version is not found."""
    pass


class StrategyRepository(BaseRepository):
    """Repository for strategy and strategy version data access operations."""
    
    def create_strategy(self, data: StrategyCreate) -> dict:
        """
        Create a new strategy.
        
        Args:
            data: Strategy creation data
        
        Returns:
            Created strategy as dictionary
        
        Raises:
            ValueError: If source_type, direction, or status is invalid
        """
        self._require_allowed(data.source_type, STRATEGY_SOURCE_TYPES, "source_type")
        self._require_allowed(data.direction, STRATEGY_DIRECTIONS, "direction")
        self._require_allowed(data.status, STRATEGY_STATUSES, "status")
        
        strategy_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO strategies (
                    id, name, class_name, source_type, timeframe, direction,
                    file_path, params_path, status, current_version_id,
                    is_demo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    strategy_id,
                    data.name,
                    data.class_name,
                    data.source_type,
                    data.timeframe,
                    data.direction,
                    data.file_path,
                    data.params_path,
                    data.status,
                    None,  # current_version_id
                    1 if data.is_demo else 0,
                    now,
                    now,
                )
            )
        
        return self.get_strategy(strategy_id)
    
    def get_strategy(self, strategy_id: str) -> Optional[dict]:
        """
        Get a strategy by ID.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            Strategy as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM strategies WHERE id = ?",
            (strategy_id,)
        )
        
        if row:
            strategy = self._row_to_dict(row)
            # Convert is_demo from int to bool
            strategy["is_demo"] = bool(strategy["is_demo"])
            return strategy
        return None
    
    def list_strategies(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """
        List strategies with optional filters.
        
        Args:
            status: Filter by status
            source_type: Filter by source type
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of strategy dictionaries
        """
        limit = self._normalize_limit(limit, default=50, max_value=500)
        
        query = "SELECT * FROM strategies WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = fetch_all(query, tuple(params))
        strategies = []
        for row in rows:
            strategy = self._row_to_dict(row)
            strategy["is_demo"] = bool(strategy["is_demo"])
            strategies.append(strategy)
        return strategies
    
    def update_strategy(self, strategy_id: str, data: StrategyUpdate) -> dict:
        """
        Update a strategy.
        
        Args:
            strategy_id: Strategy UUID
            data: Update data
        
        Returns:
            Updated strategy as dictionary
        
        Raises:
            StrategyNotFoundError: If strategy does not exist
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy {strategy_id} not found")
        
        # Validate direction and status if provided
        if data.direction:
            self._require_allowed(data.direction, STRATEGY_DIRECTIONS, "direction")
        if data.status:
            self._require_allowed(data.status, STRATEGY_STATUSES, "status")
        
        now = self._now()
        
        # Build update fields
        update_fields = []
        params = []
        
        if data.name is not None:
            update_fields.append("name = ?")
            params.append(data.name)
        
        if data.class_name is not None:
            update_fields.append("class_name = ?")
            params.append(data.class_name)
        
        if data.timeframe is not None:
            update_fields.append("timeframe = ?")
            params.append(data.timeframe)
        
        if data.direction is not None:
            update_fields.append("direction = ?")
            params.append(data.direction)
        
        if data.file_path is not None:
            update_fields.append("file_path = ?")
            params.append(data.file_path)
        
        if data.params_path is not None:
            update_fields.append("params_path = ?")
            params.append(data.params_path)
        
        if data.status is not None:
            update_fields.append("status = ?")
            params.append(data.status)
        
        if update_fields:
            update_fields.append("updated_at = ?")
            params.append(now)
            params.append(strategy_id)
            
            query = f"UPDATE strategies SET {', '.join(update_fields)} WHERE id = ?"
            execute(query, tuple(params))
        
        return self.get_strategy(strategy_id)
    
    def archive_strategy(self, strategy_id: str) -> dict:
        """
        Archive a strategy.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            Updated strategy as dictionary
        
        Raises:
            StrategyNotFoundError: If strategy does not exist
        """
        return self.update_strategy(strategy_id, StrategyUpdate(status="archived"))
    
    def create_version(self, data: StrategyVersionCreate) -> dict:
        """
        Create a new strategy version.
        
        Args:
            data: Version creation data
        
        Returns:
            Created version as dictionary
        
        Raises:
            StrategyNotFoundError: If strategy does not exist
        """
        # Verify strategy exists
        strategy = self.get_strategy(data.strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy {data.strategy_id} not found")
        
        # Auto-increment version number if not provided
        if data.version_number is None:
            latest_version = fetch_one(
                "SELECT MAX(version_number) as max_version FROM strategy_versions WHERE strategy_id = ?",
                (data.strategy_id,)
            )
            data.version_number = (latest_version["max_version"] or 0) + 1
        
        version_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO strategy_versions (
                    id, strategy_id, version_number, py_path, json_path,
                    spec_json, params_json, code_hash, created_from_run_id,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    data.strategy_id,
                    data.version_number,
                    data.py_path,
                    data.json_path,
                    self._json_dumps(data.spec) if data.spec else None,
                    self._json_dumps(data.params) if data.params else None,
                    data.code_hash,
                    data.created_from_run_id,
                    data.notes,
                    now,
                )
            )
            
            # If this is the first version, set it as current
            if data.version_number == 1:
                conn.execute(
                    "UPDATE strategies SET current_version_id = ?, updated_at = ? WHERE id = ?",
                    (version_id, now, data.strategy_id)
                )
        
        return self.get_version(version_id)
    
    def get_version(self, version_id: str) -> Optional[dict]:
        """
        Get a strategy version by ID.
        
        Args:
            version_id: Version UUID
        
        Returns:
            Version as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM strategy_versions WHERE id = ?",
            (version_id,)
        )
        
        if row:
            version = self._deserialize_version(row)
            # Check if this is the current version
            strategy = self.get_strategy(version["strategy_id"])
            if strategy and strategy.get("current_version_id"):
                version["is_current"] = (version["id"] == strategy["current_version_id"])
            else:
                version["is_current"] = False
            return version
        return None
    
    def list_versions(self, strategy_id: str) -> List[dict]:
        """
        List all versions for a strategy.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            List of version dictionaries
        """
        rows = fetch_all(
            "SELECT * FROM strategy_versions WHERE strategy_id = ? ORDER BY version_number DESC",
            (strategy_id,)
        )
        
        versions = [self._deserialize_version(row) for row in rows]
        
        # Mark current version
        strategy = self.get_strategy(strategy_id)
        if strategy and strategy.get("current_version_id"):
            for version in versions:
                version["is_current"] = (version["id"] == strategy["current_version_id"])
        else:
            for version in versions:
                version["is_current"] = False
        
        return versions
    
    def set_current_version(self, strategy_id: str, version_id: str) -> dict:
        """
        Set the current version for a strategy.
        
        Args:
            strategy_id: Strategy UUID
            version_id: Version UUID
        
        Returns:
            Updated strategy as dictionary
        
        Raises:
            StrategyNotFoundError: If strategy does not exist
            StrategyVersionNotFoundError: If version does not exist
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy {strategy_id} not found")
        
        version = self.get_version(version_id)
        if not version:
            raise StrategyVersionNotFoundError(f"Version {version_id} not found")
        
        # Verify version belongs to strategy
        if version["strategy_id"] != strategy_id:
            raise StrategyVersionNotFoundError(f"Version {version_id} does not belong to strategy {strategy_id}")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                "UPDATE strategies SET current_version_id = ?, updated_at = ? WHERE id = ?",
                (version_id, now, strategy_id)
            )
        
        return self.get_strategy(strategy_id)
    
    def get_current_version(self, strategy_id: str) -> Optional[dict]:
        """
        Get the current version for a strategy.
        
        Args:
            strategy_id: Strategy UUID
        
        Returns:
            Current version as dictionary, or None if not found
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy or not strategy.get("current_version_id"):
            return None
        
        version = self.get_version(strategy["current_version_id"])
        if version:
            version["is_current"] = True
        
        return version
    
    def delete_demo_strategies(self) -> int:
        """
        Delete all demo strategies.
        
        Returns:
            Number of strategies deleted
        """
        with transaction() as conn:
            # First, delete versions for demo strategies
            cursor = conn.execute(
                """
                DELETE FROM strategy_versions 
                WHERE strategy_id IN (SELECT id FROM strategies WHERE is_demo = 1)
                """
            )
            versions_deleted = cursor.rowcount
            
            # Then delete demo strategies
            cursor = conn.execute("DELETE FROM strategies WHERE is_demo = 1")
            strategies_deleted = cursor.rowcount
        
        return strategies_deleted
    
    def _deserialize_version(self, row: dict) -> dict:
        """
        Deserialize a version row, converting JSON fields to objects.
        
        Args:
            row: Raw database row
        
        Returns:
            Deserialized version dictionary
        """
        if row.get("spec_json"):
            row["spec"] = self._json_loads(row["spec_json"])
        else:
            row["spec"] = None
        del row["spec_json"]
        
        if row.get("params_json"):
            row["params"] = self._json_loads(row["params_json"])
        else:
            row["params"] = None
        del row["params_json"]
        
        return row
