"""
Backend exception types for repository and service errors.
"""
from typing import Any, Optional


class RepositoryError(Exception):
    """Base class for backend repository/service errors."""
    error_type = "repository_error"
    status_code = 500

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(RepositoryError):
    """Raised when a requested resource does not exist."""
    error_type = "not_found"
    status_code = 404


class ValidationError(RepositoryError):
    """Raised when request data or domain values are invalid."""
    error_type = "validation_error"
    status_code = 400


class ConflictError(RepositoryError):
    """Raised when a request conflicts with existing state."""
    error_type = "conflict"
    status_code = 409
