"""
FastAPI exception handlers for clean, safe API error responses.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.errors import ConflictError, NotFoundError, RepositoryError, ValidationError


def error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    """Build the standard API error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "type": error_type,
            "message": message,
            "details": details or {},
        },
    )


def _http_error_type(status_code: int) -> str:
    if status_code == 400:
        return "validation_error"
    if status_code == 404:
        return "not_found"
    if status_code == 409:
        return "conflict"
    return "system_error" if status_code >= 500 else "http_error"


def _safe_message(detail) -> str:
    if isinstance(detail, str):
        return detail
    if detail is None:
        return "Request failed"
    if isinstance(detail, Exception):
        return str(detail)
    return "Request failed"


def _make_serializable(obj):
    """Recursively convert objects to JSON-serializable types."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, Exception):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, set):
        return [_make_serializable(item) for item in obj]
    return str(obj)


def register_exception_handlers(app: FastAPI) -> None:
    """Register HER API exception handlers on a FastAPI app."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return error_response(exc.status_code, exc.error_type, exc.message, exc.details)

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError):
        return error_response(exc.status_code, exc.error_type, exc.message, exc.details)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError):
        return error_response(exc.status_code, exc.error_type, exc.message, exc.details)

    @app.exception_handler(RepositoryError)
    async def repository_handler(request: Request, exc: RepositoryError):
        return error_response(
            exc.status_code,
            exc.error_type,
            exc.message if exc.status_code < 500 else "Internal server error",
            exc.details if exc.status_code < 500 else {},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return error_response(
            exc.status_code,
            _http_error_type(exc.status_code),
            _safe_message(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        # Convert errors to JSON-serializable format
        errors = _make_serializable(exc.errors())
        
        return error_response(
            400,
            "validation_error",
            "Request validation failed",
            {"errors": errors},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return error_response(
            400,
            "validation_error",
            str(exc),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return error_response(
            500,
            "system_error",
            "Internal server error",
        )
