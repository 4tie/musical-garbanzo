"""
Base repository with common helpers for all HER repositories.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.sqlite import dict_from_row


class BaseRepository:
    """Base repository class with common helper methods."""
    SECRET_KEY_MARKERS = (
        "token",
        "secret",
        "password",
        "api_key",
        "apikey",
        "private_key",
    )
    
    @staticmethod
    def _now() -> str:
        """
        Get current UTC timestamp as ISO 8601 string.
        
        Returns:
            ISO 8601 formatted timestamp
        """
        return datetime.now(timezone.utc).isoformat()
    
    @staticmethod
    def _uuid() -> str:
        """
        Generate a new UUID string.
        
        Returns:
            UUID string
        """
        return str(uuid.uuid4())
    
    @staticmethod
    def _json_dumps(value: Any) -> str:
        """
        Serialize a value to JSON string.
        
        Args:
            value: Value to serialize
        
        Returns:
            JSON string
        """
        return json.dumps(value)
    
    @staticmethod
    def _json_loads(value: str, default: Any = None) -> Any:
        """
        Deserialize a JSON string.
        
        Args:
            value: JSON string to deserialize
            default: Default value if deserialization fails
        
        Returns:
            Deserialized value or default
        """
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @staticmethod
    def _require_allowed(value: str, allowed: List[str], field_name: str) -> None:
        """
        Validate that a value is in the allowed list.
        
        Args:
            value: Value to validate
            allowed: List of allowed values
            field_name: Name of the field (for error message)
        
        Raises:
            ValueError: If value is not in allowed list
        """
        if value not in allowed:
            raise ValueError(
                f"Invalid {field_name}: '{value}'. "
                f"Allowed values: {', '.join(allowed)}"
            )
    
    @staticmethod
    def _normalize_limit(limit: Optional[int], default: int = 50, max_value: int = 500) -> int:
        """
        Normalize a limit value to be within acceptable range.
        
        Args:
            limit: Requested limit (may be None)
            default: Default limit if not provided
            max_value: Maximum allowed limit
        
        Returns:
            Normalized limit value
        """
        if limit is None:
            return default
        if limit <= 0:
            return default
        if limit > max_value:
            return max_value
        return limit
    
    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        """
        Convert a sqlite3.Row to a dictionary.
        
        Args:
            row: SQLite row object
        
        Returns:
            Dictionary representation of the row
        """
        return dict_from_row(row)
    
    @staticmethod
    def _rows_to_dicts(rows) -> List[Dict[str, Any]]:
        """
        Convert a list of sqlite3.Row objects to dictionaries.
        
        Args:
            rows: List of SQLite row objects
        
        Returns:
            List of dictionaries
        """
        return [dict_from_row(row) for row in rows]

    @classmethod
    def _sanitize_secret_like(cls, value: Any) -> Any:
        """
        Redact values under obvious secret-like keys in nested JSON objects.

        This intentionally keeps shape and non-secret values intact so logs and
        audit records remain useful for traceability without storing raw secrets.
        """
        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                key_lower = str(key).lower()
                if any(marker in key_lower for marker in cls.SECRET_KEY_MARKERS):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = cls._sanitize_secret_like(item)
            return sanitized

        if isinstance(value, list):
            return [cls._sanitize_secret_like(item) for item in value]

        return value
