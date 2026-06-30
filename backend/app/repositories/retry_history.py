"""
Repository for Retry History operations.
"""
from typing import Optional, List

from app.core.constants import RETRY_STATUSES
from app.db.sqlite import fetch_one, fetch_all, transaction
from app.repositories.base import BaseRepository
from app.schemas.retry_history import RetryHistoryCreate


class RetryHistoryRepository(BaseRepository):
    """Repository for retry history data access operations."""
    
    def create_retry_entry(self, data: RetryHistoryCreate) -> dict:
        """
        Create a retry history entry.
        
        Args:
            data: Retry history creation data
        
        Returns:
            Created retry entry as dictionary
        
        Raises:
            ValueError: If retry status is invalid
        """
        self._require_allowed(data.status, RETRY_STATUSES, "status")
        
        retry_id = self._uuid()
        now = self._now()
        reason = data.reason or data.error_message or data.stage_key or "retry requested"
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO retry_history (
                    id, run_id, parent_run_id, attempt_number, reason,
                    stage_key, status, error_message, proposed_fix_json,
                    applied_fix_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    retry_id,
                    data.run_id,
                    data.parent_run_id,
                    data.attempt_number,
                    reason,
                    data.stage_key,
                    data.status,
                    data.error_message,
                    self._json_dumps(data.proposed_fix) if data.proposed_fix else None,
                    self._json_dumps(data.applied_fix) if data.applied_fix else None,
                    now,
                )
            )
        
        return self.get_retry_entry(retry_id)
    
    def get_retry_entry(self, retry_id: str) -> Optional[dict]:
        """
        Get a retry entry by ID.
        
        Args:
            retry_id: Retry UUID
        
        Returns:
            Retry entry as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM retry_history WHERE id = ?",
            (retry_id,)
        )
        
        if row:
            return self._deserialize_retry(self._row_to_dict(row))
        return None
    
    def list_retry_history(self, run_id: str) -> List[dict]:
        """
        List retry history for a run.
        
        Args:
            run_id: Run UUID
        
        Returns:
            List of retry entry dictionaries
        """
        rows = fetch_all(
            "SELECT * FROM retry_history WHERE run_id = ? ORDER BY created_at DESC",
            (run_id,)
        )
        
        return [self._deserialize_retry(self._row_to_dict(row)) for row in rows]
    
    def complete_retry(
        self,
        retry_id: str,
        status: str,
        applied_fix: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> dict:
        """
        Complete a retry entry.
        
        Args:
            retry_id: Retry UUID
            status: Final status (applied, failed, rejected, skipped)
            applied_fix: Applied fix as JSON
            error_message: Error message if failed
        
        Returns:
            Updated retry entry as dictionary
        
        Raises:
            ValueError: If retry entry not found or status invalid
        """
        self._require_allowed(status, RETRY_STATUSES, "status")
        
        retry = self.get_retry_entry(retry_id)
        if not retry:
            raise ValueError(f"Retry entry {retry_id} not found")
        
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                """
                UPDATE retry_history
                SET status = ?, applied_fix_json = ?, error_message = ?, completed_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    self._json_dumps(applied_fix) if applied_fix else None,
                    error_message,
                    now,
                    retry_id,
                )
            )
        
        return self.get_retry_entry(retry_id)
    
    def _deserialize_retry(self, row: dict) -> dict:
        """Deserialize a retry row, converting JSON fields to objects."""
        if row.get("proposed_fix_json"):
            row["proposed_fix"] = self._json_loads(row["proposed_fix_json"])
        else:
            row["proposed_fix"] = None
        del row["proposed_fix_json"]
        
        if row.get("applied_fix_json"):
            row["applied_fix"] = self._json_loads(row["applied_fix_json"])
        else:
            row["applied_fix"] = None
        del row["applied_fix_json"]
        
        return row
