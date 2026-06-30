"""
Repository for Run Stage operations.
"""
from typing import Optional, List, Any

from app.core.constants import (
    STAGE_STATUSES,
    DEFAULT_RUN_STAGES,
)
from app.db.sqlite import fetch_one, fetch_all, execute, transaction
from app.repositories.base import BaseRepository


class RunStageNotFoundError(Exception):
    """Raised when a run stage is not found."""
    pass


class RunStageRepository(BaseRepository):
    """Repository for run stage data access operations."""
    
    def create_stage(
        self,
        run_id: str,
        stage_key: str,
        stage_name: str,
        order_index: int,
        input_data: Optional[Any] = None,
    ) -> dict:
        """
        Create a new run stage.
        
        Args:
            run_id: Parent run ID
            stage_key: Stage identifier
            stage_name: Human-readable stage name
            order_index: Execution order
            input_data: Optional input data
        
        Returns:
            Created stage as dictionary
        """
        stage_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO run_stages (
                    id, run_id, stage_key, stage_name, order_index,
                    status, input_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stage_id,
                    run_id,
                    stage_key,
                    stage_name,
                    order_index,
                    "pending",
                    self._json_dumps(input_data) if input_data else None,
                    now,
                    now,
                )
            )
        
        return self.get_stage(run_id, stage_key)
    
    def create_default_stages(self, run_id: str) -> List[dict]:
        """
        Create default stages for a run.
        
        Args:
            run_id: Parent run ID
        
        Returns:
            List of created stages
        """
        stages = []
        
        for stage_def in DEFAULT_RUN_STAGES:
            stage = self.create_stage(
                run_id=run_id,
                stage_key=stage_def["stage_key"],
                stage_name=stage_def["stage_name"],
                order_index=stage_def["order_index"],
            )
            stages.append(stage)
        
        return stages
    
    def get_stage(self, run_id: str, stage_key: str) -> Optional[dict]:
        """
        Get a stage by run ID and stage key.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
        
        Returns:
            Stage as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM run_stages WHERE run_id = ? AND stage_key = ?",
            (run_id, stage_key)
        )
        
        if row:
            return self._deserialize_stage(row)
        return None
    
    def list_stages(self, run_id: str) -> List[dict]:
        """
        List all stages for a run, ordered by order_index.
        
        Args:
            run_id: Run ID
        
        Returns:
            List of stage dictionaries
        """
        rows = fetch_all(
            "SELECT * FROM run_stages WHERE run_id = ? ORDER BY order_index",
            (run_id,)
        )
        
        return [self._deserialize_stage(row) for row in rows]
    
    def update_stage(
        self,
        run_id: str,
        stage_key: str,
        data: dict,
    ) -> dict:
        """
        Update a stage.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            data: Update data
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        # Build update fields
        update_fields = []
        params = []
        
        if "stage_name" in data and data["stage_name"] is not None:
            update_fields.append("stage_name = ?")
            params.append(data["stage_name"])
        
        if "input_data" in data and data["input_data"] is not None:
            update_fields.append("input_json = ?")
            params.append(self._json_dumps(data["input_data"]))
        
        if "output_data" in data and data["output_data"] is not None:
            update_fields.append("output_json = ?")
            params.append(self._json_dumps(data["output_data"]))
        
        if "error_data" in data and data["error_data"] is not None:
            update_fields.append("error_json = ?")
            params.append(self._json_dumps(data["error_data"]))
        
        if "logs_summary" in data and data["logs_summary"] is not None:
            update_fields.append("logs_summary = ?")
            params.append(data["logs_summary"])
        
        if update_fields:
            update_fields.append("updated_at = ?")
            params.append(now)
            params.append(run_id)
            params.append(stage_key)
            
            query = f"UPDATE run_stages SET {', '.join(update_fields)} WHERE run_id = ? AND stage_key = ?"
            execute(query, tuple(params))
        
        return self.get_stage(run_id, stage_key)
    
    def start_stage(
        self,
        run_id: str,
        stage_key: str,
        input_data: Optional[Any] = None,
    ) -> dict:
        """
        Start a stage.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            input_data: Optional input data
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE run_stages 
                SET status = ?, started_at = ?, updated_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                ("running", now, now, run_id, stage_key)
            )
            
            if input_data:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET input_json = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (self._json_dumps(input_data), now, run_id, stage_key)
                )
        
        return self.get_stage(run_id, stage_key)
    
    def complete_stage(
        self,
        run_id: str,
        stage_key: str,
        output_data: Optional[Any] = None,
        logs_summary: Optional[str] = None,
    ) -> dict:
        """
        Complete a stage.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            output_data: Optional output data
            logs_summary: Optional log summary
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        # Calculate duration if started_at exists
        duration_ms = None
        if stage.get("started_at"):
            started = self._parse_timestamp(stage["started_at"])
            completed = self._parse_timestamp(now)
            duration_ms = int((completed - started).total_seconds() * 1000)
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE run_stages 
                SET status = ?, completed_at = ?, duration_ms = ?, updated_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                ("passed", now, duration_ms, now, run_id, stage_key)
            )
            
            if output_data:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET output_json = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (self._json_dumps(output_data), now, run_id, stage_key)
                )
            
            if logs_summary:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET logs_summary = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (logs_summary, now, run_id, stage_key)
                )
        
        return self.get_stage(run_id, stage_key)
    
    def fail_stage(
        self,
        run_id: str,
        stage_key: str,
        error_data: Optional[Any] = None,
        logs_summary: Optional[str] = None,
    ) -> dict:
        """
        Fail a stage.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            error_data: Optional error data
            logs_summary: Optional log summary
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        # Calculate duration if started_at exists
        duration_ms = None
        if stage.get("started_at"):
            started = self._parse_timestamp(stage["started_at"])
            completed = self._parse_timestamp(now)
            duration_ms = int((completed - started).total_seconds() * 1000)
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE run_stages 
                SET status = ?, completed_at = ?, duration_ms = ?, updated_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                ("failed", now, duration_ms, now, run_id, stage_key)
            )
            
            if error_data:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET error_json = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (self._json_dumps(error_data), now, run_id, stage_key)
                )
            
            if logs_summary:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET logs_summary = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (logs_summary, now, run_id, stage_key)
                )
        
        return self.get_stage(run_id, stage_key)
    
    def skip_stage(
        self,
        run_id: str,
        stage_key: str,
        reason: Optional[str] = None,
    ) -> dict:
        """
        Skip a stage.
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            reason: Optional skip reason
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE run_stages 
                SET status = ?, completed_at = ?, updated_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                ("skipped", now, now, run_id, stage_key)
            )
            
            if reason:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET logs_summary = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (reason, now, run_id, stage_key)
                )
        
        return self.get_stage(run_id, stage_key)
    
    def reset_stages(self, run_id: str) -> int:
        """
        Reset all stages for a run to pending status.
        
        Args:
            run_id: Run ID
        
        Returns:
            Number of stages reset
        """
        with transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE run_stages 
                SET status = 'pending', started_at = NULL, completed_at = NULL, 
                    duration_ms = NULL, input_json = NULL, output_json = NULL, 
                    error_json = NULL, updated_at = ?
                WHERE run_id = ?
                """,
                (self._now(), run_id)
            )
            return cursor.rowcount
    
    def create_baseline_stages(self, run_id: str) -> List[dict]:
        """
        Create baseline evaluation pipeline stages for a run.
        
        Args:
            run_id: Parent run ID
        
        Returns:
            List of created stages
        """
        from app.core.constants import BASELINE_PIPELINE_STAGES
        
        stages = []
        for order_index, stage_key in enumerate(BASELINE_PIPELINE_STAGES, start=1):
            stage_name = stage_key.replace("_", " ").title()
            stage = self.create_stage(
                run_id=run_id,
                stage_key=stage_key,
                stage_name=stage_name,
                order_index=order_index,
            )
            stages.append(stage)
        
        return stages
    
    def mark_stage_waiting(
        self,
        run_id: str,
        stage_key: str,
        message: Optional[str] = None,
    ) -> dict:
        """
        Mark a stage as waiting (e.g., for user confirmation).
        
        Args:
            run_id: Run ID
            stage_key: Stage key
            message: Optional waiting message
        
        Returns:
            Updated stage as dictionary
        
        Raises:
            RunStageNotFoundError: If stage does not exist
        """
        stage = self.get_stage(run_id, stage_key)
        if not stage:
            raise RunStageNotFoundError(f"Stage {stage_key} not found for run {run_id}")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE run_stages 
                SET status = ?, updated_at = ?
                WHERE run_id = ? AND stage_key = ?
                """,
                ("waiting", now, run_id, stage_key)
            )
            
            if message:
                conn.execute(
                    """
                    UPDATE run_stages 
                    SET logs_summary = ?, updated_at = ?
                    WHERE run_id = ? AND stage_key = ?
                    """,
                    (message, now, run_id, stage_key)
                )
        
        return self.get_stage(run_id, stage_key)
    
    def _deserialize_stage(self, row: dict) -> dict:
        """
        Deserialize a stage row, converting JSON fields to objects.
        
        Args:
            row: Raw database row
        
        Returns:
            Deserialized stage dictionary
        """
        if row.get("input_json"):
            row["input"] = self._json_loads(row["input_json"])
        else:
            row["input"] = None
        del row["input_json"]
        
        if row.get("output_json"):
            row["output"] = self._json_loads(row["output_json"])
        else:
            row["output"] = None
        del row["output_json"]
        
        if row.get("error_json"):
            row["error"] = self._json_loads(row["error_json"])
        else:
            row["error"] = None
        del row["error_json"]
        
        return row
    
    def _parse_timestamp(self, timestamp_str: str):
        """Parse an ISO timestamp string to datetime."""
        from datetime import datetime, timezone
        return datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
