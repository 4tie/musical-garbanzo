# HER Backend Architecture

## Overview

HER backend is built with FastAPI and follows a layered architecture pattern. This document describes the architectural rules, patterns, and conventions used throughout the backend codebase.

## Architecture Layers

```
┌─────────────────────────────────────┐
│         API Routers                 │
│  (FastAPI endpoints, validation)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Repository Layer                │
│  (Data access, business logic)       │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Database Layer                 │
│  (SQLite connection, helpers)       │
└─────────────────────────────────────┘
```

## Repository Layer Rules

### Purpose
The repository layer is responsible for all data access operations. It provides a clean abstraction between the API routers and the database.

### Rules

1. **No Raw SQL in API Routers**
   - All SQL queries must be contained within repository classes
   - API routers should only call repository methods
   - This separation enables testing and maintains clean boundaries

2. **No Duplicate Connection Logic**
   - All database connections must use the shared helpers in `app/db/sqlite.py`
   - Repositories should not directly call `sqlite3.connect()`
   - Use `get_connection()`, `execute()`, `fetch_one()`, `fetch_all()`, or `transaction()`

3. **No Secrets in Repository Logs**
   - Never log secret values (tokens, API keys, passwords)
   - Use masked values in debug output (e.g., `••••••••`)
   - The `SecretStr` type from Pydantic should be used for sensitive fields

4. **Use BaseRepository Helpers**
   - All repositories should inherit from `BaseRepository`
   - Use `_now()`, `_uuid()`, `_json_dumps()`, `_json_loads()` for common operations
   - Use `_require_allowed()` to validate enum values against constants
   - Use `_normalize_limit()` to sanitize pagination limits

5. **Transaction Safety**
   - Use the `transaction()` context manager for multi-step operations
   - Transactions automatically commit on success and rollback on failure
   - Always close connections (handled by helpers)

6. **Error Handling**
   - Repository methods should raise meaningful exceptions
   - Use specific exception types when possible
   - Include context in error messages

### Example Repository Pattern

```python
from app.repositories.base import BaseRepository
from app.db.sqlite import fetch_one, fetch_all, execute, transaction

class RunRepository(BaseRepository):
    def create_run(self, name: str, mode: str, config: dict) -> dict:
        """Create a new run."""
        self._require_allowed(mode, RUN_MODES, "mode")
        
        run_id = self._uuid()
        now = self._now()
        
        with transaction() as conn:
            conn.execute(
                "INSERT INTO runs (id, name, mode, status, config_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (run_id, name, mode, "created", self._json_dumps(config), now, now)
            )
        
        return self.get_run(run_id)
    
    def get_run(self, run_id: str) -> Optional[dict]:
        """Get a run by ID."""
        return fetch_one(
            "SELECT * FROM runs WHERE id = ?",
            (run_id,)
        )
```

## API Router Rules

### Purpose
API routers define HTTP endpoints, handle request validation, and delegate business logic to repositories.

### Rules

1. **No Raw SQL in Routers**
   - All database operations must go through repositories
   - Routers should focus on HTTP concerns (validation, responses)

2. **Use Pydantic for Validation**
   - Define request schemas using Pydantic models
   - Define response schemas using Pydantic models
   - Leverage Pydantic's validation for input sanitization

3. **Return Consistent Responses**
   - Use standard HTTP status codes
   - Return structured error responses
   - Include relevant metadata in responses

4. **Handle Errors Gracefully**
   - Catch repository exceptions and convert to HTTP responses
   - Never expose internal details in error messages
   - Log errors appropriately

### Example Router Pattern

```python
from fastapi import APIRouter, HTTPException
from app.repositories.run_repository import RunRepository
from app.schemas.run import RunCreateRequest, RunResponse

router = APIRouter()
run_repo = RunRepository()

@router.post("/runs", response_model=RunResponse)
def create_run(request: RunCreateRequest):
    """Create a new run."""
    try:
        run = run_repo.create_run(
            name=request.name,
            mode=request.mode,
            config=request.config
        )
        return RunResponse(**run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to create run")
```

## Constants Centralization

### Why Constants Are Centralized

1. **Type Safety**
   - Centralized constants ensure consistent values across the codebase
   - Prevents typos and invalid enum values
   - Enables validation against known sets

2. **Maintainability**
   - Single source of truth for allowed values
   - Easy to add new values without hunting through code
   - Documentation of all valid states in one place

3. **Validation**
   - Repositories can validate against these constants
   - API schemas can use these constants for validation
   - Frontend can reference these constants for UI options

### Constants File Location

All constants are defined in `app/core/constants.py`:
- `RUN_MODES` - Allowed run operation modes
- `RUN_STATUSES` - Allowed run status values
- `CLASSIFICATIONS` - Strategy classification outcomes
- `STAGE_STATUSES` - Stage execution statuses
- `STRATEGY_SOURCE_TYPES` - Strategy origin types
- `STRATEGY_DIRECTIONS` - Trading directions
- `STRATEGY_STATUSES` - Strategy lifecycle statuses
- `ARTIFACT_TYPES` - Artifact file types
- `LOG_LEVELS` - Logging severity levels
- `RETRY_STATUSES` - Retry operation statuses
- `AUDIT_ACTORS` - System actor types
- `DEFAULT_RUN_STAGES` - Default AutoQuant pipeline stages

## SQLite Transaction Handling

### Transaction Pattern

HER uses a context manager pattern for transactions:

```python
from app.db.sqlite import transaction

with transaction() as conn:
    # Multiple operations
    conn.execute("INSERT INTO ...")
    conn.execute("UPDATE ...")
    conn.execute("DELETE FROM ...")
    # Automatically committed on success
```

### Transaction Behavior

1. **Automatic Commit**
   - If no exception occurs, changes are committed
   - Context manager handles commit on exit

2. **Automatic Rollback**
   - If any exception occurs, all changes are rolled back
   - Ensures data consistency

3. **Connection Management**
   - Connection is automatically closed after transaction
   - Prevents connection leaks

4. **Foreign Keys**
   - Foreign key constraints are enforced
   - Referential integrity is maintained

### When to Use Transactions

- Multi-step operations that must succeed together
- Operations that modify multiple tables
- Operations that require atomicity
- Any write operation that could fail mid-process

### When Not to Use Transactions

- Simple single-row inserts/updates (use `execute()`)
- Read-only operations (use `fetch_one()` or `fetch_all()`)
- Bulk operations where partial failure is acceptable

## Database Helper Functions

### Available Helpers

Located in `app/db/sqlite.py`:

1. **`get_database_path()`** - Get absolute path to database file
2. **`get_connection()`** - Get a new SQLite connection with row factory
3. **`dict_from_row(row)`** - Convert sqlite3.Row to dict
4. **`execute(query, params)`** - Execute a query with auto-commit
5. **`execute_many(query, params_list)`** - Execute bulk inserts
6. **`fetch_one(query, params)`** - Fetch a single row as dict
7. **`fetch_all(query, params)`** - Fetch all rows as list of dicts
8. **`transaction()`** - Context manager for transactions

### Connection Safety

All helpers ensure:
- Parent directory exists before connecting
- Row factory is configured for dict-like access
- Foreign keys are enabled
- Connections are closed after use
- Transactions are rolled back on failure

## Security Considerations

### Secret Protection

1. **Environment Variables Only**
   - Secrets stored in `.env` file
   - `.env` is in `.gitignore`
   - Never committed to version control

2. **Pydantic SecretStr**
   - Sensitive fields use `SecretStr` type
   - Automatically excluded from serialization
   - Never printed in logs or responses

3. **No Secret Logging**
   - Repository methods never log secret values
   - API responses never include secret fields
   - Debug output masks sensitive data

### Input Validation

1. **Pydantic Validation**
   - All API inputs validated by Pydantic schemas
   - Type checking and format validation
   - Custom validators for business rules

2. **Repository Validation**
   - Enum values validated against constants
   - Foreign key references validated
   - Business rule enforcement

3. **SQL Injection Prevention**
   - Always use parameterized queries
   - Never concatenate user input into SQL
   - Use `?` placeholders in queries

## Testing Strategy

### Repository Tests

- Use in-memory SQLite for isolation
- Test CRUD operations
- Test query methods
- Test transaction rollback
- Test foreign key constraints

### API Tests

- Use FastAPI TestClient
- Test all endpoints
- Test request validation
- Test error handling
- Test response schemas

### Integration Tests

- Test repository + API integration
- Test end-to-end workflows
- Test concurrent operations
- Test data consistency

## Performance Considerations

### Database Performance

1. **Indexes**
   - Strategic indexes on foreign keys
   - Indexes on common query filters
   - Indexes on timestamp columns

2. **Connection Management**
   - Connections closed after use
   - No connection pooling (single-user local app)
   - WAL mode for better concurrency

3. **Query Optimization**
   - Use `fetch_one()` for single row queries
   - Use `fetch_all()` with LIMIT for pagination
   - Avoid SELECT * when possible

### API Performance

1. **Pagination**
   - List endpoints support pagination
   - Default limit of 50, max of 500
   - Use `_normalize_limit()` helper

2. **Caching**
   - Consider caching expensive queries
   - Cache frequently accessed configuration
   - Invalidate cache on data changes

## Future Considerations

### Potential Enhancements

1. **Async Support**
   - Consider async/await for I/O operations
   - Use aiosqlite if async is needed
   - Maintain compatibility with current sync approach

2. **ORM Migration**
   - If complexity grows, consider SQLAlchemy
   - Keep repository layer as abstraction
   - Migration should be transparent to routers

3. **Database Migration**
   - If PostgreSQL is needed, use migration tool
   - Keep repository layer database-agnostic
   - Abstract SQL dialect differences

### Architectural Principles to Maintain

- Keep layers separated
- No raw SQL in routers
- Centralized constants
- Transaction safety
- Secret protection
- Testability
