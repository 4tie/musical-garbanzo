"""
Repository for Run Logs operations.
"""
from typing import Optional, List

from app.core.constants import LOG_LEVELS
from app.db.sqlite import fetch_one, fetch_all, transaction
from app.repositories.base import BaseRepository


class RunLogRepository(BaseRepository):
    """Repository for run log data access operations."""
    
    def add_log(
        self,
        run_id: str,
        level: str,
        source: str,
        message: str,
        stage_key: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> dict:
        """
        Add a log entry.
        
        Args:
            run_id: Run UUID
            level: Log level
            source: Log source
            message: Log message
            stage_key: Optional stage key
            details: Optional details dictionary
        
        Returns:
            Created log entry as dictionary
        
        Raises:
            ValueError: If log level is invalid
        """
        self._require_allowed(level, LOG_LEVELS, "level")
        
        # Sanitize details to remove secret-like values
        sanitized_details = self._sanitize_secret_like(details) if details else None
        
        log_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO run_logs (
                    id, run_id, level, source, message, stage_key, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    run_id,
                    level,
                    source,
                    message,
                    stage_key,
                    self._json_dumps(sanitized_details) if sanitized_details else None,
                    now,
                )
            )
        
        return self.get_log(log_id)
    
    def get_log(self, log_id: str) -> Optional[dict]:
        """
        Get a log entry by ID.
        
        Args:
            log_id: Log UUID
        
        Returns:
            Log entry as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM run_logs WHERE id = ?",
            (log_id,)
        )
        
        if row:
            return self._deserialize_log(self._row_to_dict(row))
        return None
    
    def list_logs(
        self,
        run_id: Optional[str] = None,
        stage_key: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """
        List log entries with optional filters.
        
        Args:
            run_id: Filter by run ID
            stage_key: Filter by stage key
            level: Filter by log level
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of log entry dictionaries
        """
        limit = self._normalize_limit(limit, default=100, max_value=1000)
        
        query = "SELECT * FROM run_logs WHERE 1=1"
        params = []
        
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        
        if stage_key:
            query += " AND stage_key = ?"
            params.append(stage_key)
        
        if level:
            query += " AND level = ?"
            params.append(level)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = fetch_all(query, tuple(params))
        return [self._deserialize_log(self._row_to_dict(row)) for row in rows]
    
    def _deserialize_log(self, row: dict) -> dict:
        """Deserialize a log row, converting JSON field to object."""
        if row.get("details_json"):
            row["details"] = self._json_loads(row["details_json"])
        else:
            row["details"] = None
        del row["details_json"]
        return row
