"""
Repository for Run operations.
"""
from typing import Optional, List

from app.core.constants import (
    RUN_MODES,
    RUN_STATUSES,
    CLASSIFICATIONS,
    DECISION_CLASSIFICATIONS,
)
from app.db.sqlite import fetch_one, fetch_all, execute, transaction
from app.repositories.base import BaseRepository
from app.repositories.run_stages import RunStageRepository
from app.schemas.runs import RunCreate, RunUpdate


class RunNotFoundError(Exception):
    """Raised when a run is not found."""
    pass


class RunRepository(BaseRepository):
    """Repository for run data access operations."""
    
    def create_run(self, data: RunCreate, create_default_stages: bool = True) -> dict:
        """
        Create a new run.
        
        Args:
            data: Run creation data
            create_default_stages: Whether to create default stages (default: True)
        
        Returns:
            Created run as dictionary
        
        Raises:
            ValueError: If mode is invalid
        """
        self._require_allowed(data.mode, RUN_MODES, "mode")
        
        run_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, name, mode, status, strategy_id, parent_run_id,
                    exchange, quote_currency, trading_mode, timeframe,
                    pairs_json, timerange, risk_profile, analysis_depth,
                    is_demo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    data.name,
                    data.mode,
                    "created",
                    data.strategy_id,
                    data.parent_run_id,
                    data.exchange,
                    data.quote_currency,
                    data.trading_mode,
                    data.timeframe,
                    self._json_dumps(data.pairs) if data.pairs else None,
                    data.timerange,
                    data.risk_profile,
                    data.analysis_depth,
                    1 if data.is_demo else 0,
                    now,
                    now,
                )
            )
        
        # Create default stages if requested
        if create_default_stages:
            stage_repo = RunStageRepository()
            stage_repo.create_default_stages(run_id)
        
        return self.get_run(run_id)
    
    def get_run(self, run_id: str) -> Optional[dict]:
        """
        Get a run by ID.
        
        Args:
            run_id: Run ID
        
        Returns:
            Run as dictionary, or None if not found
        """
        row = fetch_one("SELECT * FROM runs WHERE id = ?", (run_id,))
        if row:
            # Deserialize pairs_json
            if row.get("pairs_json"):
                row["pairs"] = self._json_loads(row["pairs_json"], default=[])
            else:
                row["pairs"] = None
            del row["pairs_json"]
            return row
        return None
    
    def list_runs(
        self,
        status: Optional[str] = None,
        classification: Optional[str] = None,
        strategy_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[dict]:
        """
        List runs with optional filters.
        
        Args:
            status: Filter by status
            classification: Filter by classification
            strategy_id: Filter by strategy ID
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of run dictionaries
        """
        limit = self._normalize_limit(limit, default=50, max_value=500)
        
        # Build query with filters
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        
        if classification:
            conditions.append("classification = ?")
            params.append(classification)
        
        if strategy_id:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)
        
        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f"""
            SELECT * FROM runs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        rows = fetch_all(query, tuple(params))
        
        # Deserialize pairs_json for each row
        for row in rows:
            if row.get("pairs_json"):
                row["pairs"] = self._json_loads(row["pairs_json"], default=[])
            else:
                row["pairs"] = None
            del row["pairs_json"]
        
        return rows
    
    def update_run(self, run_id: str, data: RunUpdate) -> dict:
        """
        Update a run.
        
        Args:
            run_id: Run ID
            data: Update data
        
        Returns:
            Updated run as dictionary
        
        Raises:
            RunNotFoundError: If run does not exist
        """
        run = self.get_run(run_id)
        if not run:
            raise RunNotFoundError(f"Run {run_id} not found")
        
        now = self._now()
        
        # Build update fields
        update_fields = []
        params = []
        
        if data.name is not None:
            update_fields.append("name = ?")
            params.append(data.name)
        
        if data.exchange is not None:
            update_fields.append("exchange = ?")
            params.append(data.exchange)
        
        if data.quote_currency is not None:
            update_fields.append("quote_currency = ?")
            params.append(data.quote_currency)
        
        if data.trading_mode is not None:
            update_fields.append("trading_mode = ?")
            params.append(data.trading_mode)
        
        if data.timeframe is not None:
            update_fields.append("timeframe = ?")
            params.append(data.timeframe)
        
        if data.pairs is not None:
            update_fields.append("pairs_json = ?")
            params.append(self._json_dumps(data.pairs))
        
        if data.timerange is not None:
            update_fields.append("timerange = ?")
            params.append(data.timerange)
        
        if data.risk_profile is not None:
            update_fields.append("risk_profile = ?")
            params.append(data.risk_profile)
        
        if data.analysis_depth is not None:
            update_fields.append("analysis_depth = ?")
            params.append(data.analysis_depth)
        
        if update_fields:
            update_fields.append("updated_at = ?")
            params.append(now)
            params.append(run_id)
            
            query = f"UPDATE runs SET {', '.join(update_fields)} WHERE id = ?"
            execute(query, tuple(params))
        
        return self.get_run(run_id)
    
    def update_status(self, run_id: str, status: str, failure_reason: Optional[str] = None) -> dict:
        """
        Update run status.
        
        Args:
            run_id: Run ID
            status: New status
            failure_reason: Optional failure reason
        
        Returns:
            Updated run as dictionary
        
        Raises:
            ValueError: If status is invalid
            RunNotFoundError: If run does not exist
        """
        self._require_allowed(status, RUN_STATUSES, "status")
        
        run = self.get_run(run_id)
        if not run:
            raise RunNotFoundError(f"Run {run_id} not found")
        
        now = self._now()
        
        # Determine if we need to set started_at or completed_at
        set_started_at = status == "running" and run["started_at"] is None
        set_completed_at = status in ["failed_controlled", "failed_system", "rejected", "exported", "cancelled"] and run["completed_at"] is None
        
        with transaction() as conn:
            if set_started_at:
                conn.execute(
                    "UPDATE runs SET status = ?, started_at = ?, updated_at = ? WHERE id = ?",
                    (status, now, now, run_id)
                )
            elif set_completed_at:
                conn.execute(
                    "UPDATE runs SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                    (status, now, now, run_id)
                )
            else:
                conn.execute(
                    "UPDATE runs SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now, run_id)
                )
            
            if failure_reason:
                conn.execute(
                    "UPDATE runs SET failure_reason = ?, updated_at = ? WHERE id = ?",
                    (failure_reason, now, run_id)
                )
        
        return self.get_run(run_id)
    
    def set_classification(self, run_id: str, classification: str) -> dict:
        """
        Set run classification.
        
        Args:
            run_id: Run ID
            classification: Classification value
        
        Returns:
            Updated run as dictionary
        
        Raises:
            ValueError: If classification is invalid
            RunNotFoundError: If run does not exist
        """
        self._require_allowed(classification, CLASSIFICATIONS, "classification")
        
        run = self.get_run(run_id)
        if not run:
            raise RunNotFoundError(f"Run {run_id} not found")
        
        now = self._now()
        
        execute(
            "UPDATE runs SET classification = ?, updated_at = ? WHERE id = ?",
            (classification, now, run_id)
        )
        
        return self.get_run(run_id)

    def set_decision_classification(self, run_id: str, classification: str) -> dict:
        """
        Set run classification from the Part 06 decision engine.

        This intentionally accepts only Part 06 safe classifications and
        rejects later lifecycle values such as approved/exported.
        """
        self._require_allowed(
            classification,
            DECISION_CLASSIFICATIONS,
            "decision classification",
        )
        return self.set_classification(run_id, classification)
    
    def mark_started(self, run_id: str) -> dict:
        """
        Mark a run as started.
        
        Args:
            run_id: Run ID
        
        Returns:
            Updated run as dictionary
        
        Raises:
            RunNotFoundError: If run does not exist
        """
        return self.update_status(run_id, "running")
    
    def mark_completed(
        self,
        run_id: str,
        status: Optional[str] = None,
        classification: Optional[str] = None,
    ) -> dict:
        """
        Mark a run as completed.
        
        Args:
            run_id: Run ID
            status: Optional final status (defaults to 'candidate')
            classification: Optional classification
        
        Returns:
            Updated run as dictionary
        
        Raises:
            RunNotFoundError: If run does not exist
        """
        if status is None:
            status = "candidate"
        
        run = self.get_run(run_id)
        if not run:
            raise RunNotFoundError(f"Run {run_id} not found")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                "UPDATE runs SET status = ?, completed_at = ?, updated_at = ? WHERE id = ?",
                (status, now, now, run_id)
            )
            
            if classification:
                self._require_allowed(classification, CLASSIFICATIONS, "classification")
                conn.execute(
                    "UPDATE runs SET classification = ?, updated_at = ? WHERE id = ?",
                    (classification, now, run_id)
                )
        
        return self.get_run(run_id)
    
    def mark_failed(self, run_id: str, failure_type: str, reason: str) -> dict:
        """
        Mark a run as failed.
        
        Args:
            run_id: Run ID
            failure_type: Type of failure (controlled or system)
            reason: Failure reason
        
        Returns:
            Updated run as dictionary
        
        Raises:
            ValueError: If failure_type is invalid
            RunNotFoundError: If run does not exist
        """
        if failure_type not in ["controlled", "system"]:
            raise ValueError(f"Invalid failure_type: {failure_type}. Must be 'controlled' or 'system'")
        
        status = "failed_controlled" if failure_type == "controlled" else "failed_system"
        
        return self.update_status(run_id, status, failure_reason=reason)
    
    def delete_demo_runs(self) -> int:
        """
        Delete all demo runs.
        
        Returns:
            Number of runs deleted
        """
        with transaction() as conn:
            cursor = conn.execute("DELETE FROM runs WHERE is_demo = 1")
            return cursor.rowcount
