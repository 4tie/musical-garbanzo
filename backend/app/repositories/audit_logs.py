"""
Repository for Audit Logs operations.
"""
from typing import Optional, List

from app.core.constants import AUDIT_ACTORS
from app.db.sqlite import fetch_one, fetch_all, transaction
from app.repositories.base import BaseRepository
from app.schemas.audit_logs import AuditLogCreate


class AuditLogRepository(BaseRepository):
    """Repository for audit log data access operations."""
    
    def create_audit_log(self, data: AuditLogCreate | dict) -> dict:
        """
        Create an audit log entry.
        
        Args:
            data: Audit log creation data
        
        Returns:
            Created audit log as dictionary
        
        Raises:
            ValueError: If actor is invalid
        """
        if isinstance(data, dict):
            data = AuditLogCreate(
                run_id=data.get("run_id"),
                actor=data.get("actor", "system"),
                action_type=data.get("action_type") or data.get("action") or "unknown",
                target_type=data.get("target_type") or data.get("resource_type"),
                target_id=data.get("target_id") or data.get("resource_id"),
                before=data.get("before"),
                after=data.get("after"),
                description=data.get("description"),
                approved=data.get("approved", False),
                notes=data.get("notes"),
            )

        self._require_allowed(data.actor, AUDIT_ACTORS, "actor")
        
        audit_id = self._uuid()
        now = self._now()
        before = self._sanitize_secret_like(data.before) if data.before else None
        after = self._sanitize_secret_like(data.after) if data.after else None
        description = data.description or data.notes or data.action_type
        
        with transaction() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    id, run_id, actor, action_type, target_type, target_id,
                    description, before_json, after_json, changed_files_json,
                    rollback_path, approved, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    data.run_id,
                    data.actor,
                    data.action_type,
                    data.target_type,
                    data.target_id,
                    description,
                    self._json_dumps(before) if before else None,
                    self._json_dumps(after) if after else None,
                    self._json_dumps(data.changed_files) if data.changed_files else None,
                    data.rollback_path,
                    1 if data.approved else 0,
                    data.notes,
                    now,
                )
            )
        
        return self.get_audit_log(audit_id)
    
    def get_audit_log(self, audit_id: str) -> Optional[dict]:
        """
        Get an audit log entry by ID.
        
        Args:
            audit_id: Audit log UUID
        
        Returns:
            Audit log as dictionary, or None if not found
        """
        row = fetch_one(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,)
        )
        
        if row:
            return self._deserialize_audit(self._row_to_dict(row))
        return None
    
    def list_audit_logs(
        self,
        run_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """
        List audit logs with optional filters.
        
        Args:
            run_id: Filter by run ID
            action_type: Filter by action type
            limit: Maximum number of results
            offset: Offset for pagination
        
        Returns:
            List of audit log dictionaries
        """
        limit = self._normalize_limit(limit, default=100, max_value=1000)
        
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        
        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        rows = fetch_all(query, tuple(params))
        return [self._deserialize_audit(self._row_to_dict(row)) for row in rows]
    
    def _deserialize_audit(self, row: dict) -> dict:
        """Deserialize an audit log row, converting JSON fields to objects."""
        if row.get("before_json"):
            row["before"] = self._json_loads(row["before_json"])
        else:
            row["before"] = None
        del row["before_json"]
        
        if row.get("after_json"):
            row["after"] = self._json_loads(row["after_json"])
        else:
            row["after"] = None
        del row["after_json"]
        
        if row.get("changed_files_json"):
            row["changed_files"] = self._json_loads(row["changed_files_json"])
        else:
            row["changed_files"] = None
        del row["changed_files_json"]
        
        # Convert approved from int to bool
        row["approved"] = bool(row["approved"])
        
        return row
