# Part 03 Backend and Database Plan

## Part 03 Goal

Build the backend core and database foundation for HER AutoQuant. This part establishes the data models, repository layer, API routers, and testing infrastructure needed to support the future AutoQuant pipeline.

## Confirmed Scope

Part 03 will:

1. **Database Schema Expansion**
   - Extend SQLite schema with AutoQuant-specific tables
   - Create tables for runs, strategies, artifacts, metrics, logs, and audit trail
   - Add foreign key relationships and indexes
   - Create migration scripts for new tables

2. **Repository Layer**
   - Build repository classes for each domain entity
   - Implement CRUD operations using direct sqlite3
   - Add query methods for common access patterns
   - Ensure transaction safety and error handling

3. **Pydantic Schemas**
   - Create request/response schemas for API endpoints
   - Define data validation rules
   - Separate internal models from API contracts
   - Ensure secrets are never exposed in schemas

4. **API Routers**
   - Create routers for runs, strategies, artifacts, and metrics
   - Implement RESTful endpoints with proper HTTP methods
   - Add pagination, filtering, and sorting where appropriate
   - Integrate with repository layer

5. **Testing Infrastructure**
   - Write repository tests with in-memory SQLite
   - Write API endpoint tests with TestClient
   - Add seed data for development and testing
   - Ensure test coverage for critical paths

6. **Documentation**
   - Document database schema
   - Document API endpoints
   - Update project structure documentation
   - Add usage examples

## Explicit Non-Goals

Part 03 will NOT:

- ❌ Run Freqtrade backtests
- ❌ Run Hyperopt optimization
- ❌ Download market data
- ❌ Generate strategy code
- ❌ Call Ollama for real strategy generation
- ❌ Send Discord notifications
- ❌ Build full AutoQuant UI workflow
- ❌ Add Docker/cloud/PostgreSQL/SaaS logic
- ❌ Implement the complete AutoQuant decision engine
- ❌ Add real trading execution

## Database Approach

### Technology Stack
- **Database:** SQLite (file-based, local-only)
- **Access Layer:** Direct sqlite3 (no ORM)
- **Migrations:** Explicit Python migration functions
- **Connection Management:** Context managers for transaction safety

### Rationale
- SQLite is perfect for local-only single-user application
- Direct sqlite3 provides full control and simplicity
- No ORM overhead or complexity
- Easy to migrate to PostgreSQL if needed later
- Consistent with Part 02 approach

### Connection Pattern
```python
# Continue using existing pattern from Part 02
from app.db.sqlite import get_connection

def some_repository_function():
    conn = get_connection()
    try:
        # Execute queries
        conn.execute(...)
        conn.commit()
    finally:
        conn.close()
```

## Tables to Create

### 1. runs
Stores AutoQuant run lifecycle data.

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,  -- pending, running, completed, failed, cancelled
    mode TEXT NOT NULL,    -- upload, generate, repair
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    config_json TEXT NOT NULL
);

CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_runs_created_at ON runs(created_at);
```

### 2. strategies
Stores strategy metadata and configurations.

```sql
CREATE TABLE strategies (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    family TEXT,              -- trend_following, mean_reversion, etc.
    timeframe TEXT,
    direction TEXT,           -- long, short, both
    source TEXT,              -- uploaded, generated, repaired
    file_path TEXT,
    config_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX idx_strategies_run_id ON strategies(run_id);
CREATE INDEX idx_strategies_family ON strategies(family);
```

### 3. artifacts
Stores generated artifacts and their metadata.

```sql
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,  -- strategy_file, config, backtest_result, report, etc.
    file_path TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX idx_artifacts_run_id ON artifacts(run_id);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
```

### 4. backtest_results
Stores Freqtrade backtest results.

```sql
CREATE TABLE backtest_results (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timerange TEXT,
    net_profit REAL,
    profit_factor REAL,
    sharpe_ratio REAL,
    calmar_ratio REAL,
    max_drawdown REAL,
    max_drawdown_abs REAL,
    trade_count INTEGER,
    win_rate REAL,
    avg_win REAL,
    avg_loss REAL,
    expectancy REAL,
    start_date TEXT,
    end_date TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id) ON DELETE CASCADE
);

CREATE INDEX idx_backtest_results_run_id ON backtest_results(run_id);
CREATE INDEX idx_backtest_results_strategy_id ON backtest_results(strategy_id);
```

### 5. metrics
Stores run-level metrics and KPIs.

```sql
CREATE TABLE metrics (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX idx_metrics_run_id ON metrics(run_id);
CREATE INDEX idx_metrics_name ON metrics(metric_name);
```

### 6. run_logs
Stores detailed logs for each run.

```sql
CREATE TABLE run_logs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    level TEXT NOT NULL,      -- debug, info, warning, error
    stage TEXT,               -- validation, backtest, analysis, etc.
    message TEXT NOT NULL,
    details_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX idx_run_logs_run_id ON run_logs(run_id);
CREATE INDEX idx_run_logs_created_at ON run_logs(created_at);
CREATE INDEX idx_run_logs_level ON run_logs(level);
```

### 7. audit_log
Stores audit trail for important actions.

```sql
CREATE TABLE audit_log (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,     -- run_created, run_deleted, strategy_exported, etc.
    entity_type TEXT NOT NULL, -- run, strategy, artifact, etc.
    entity_id TEXT NOT NULL,
    user_context_json TEXT,
    changes_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
```

### 8. retry_attempts
Stores retry information for failed operations.

```sql
CREATE TABLE retry_attempts (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,     -- pending, success, failed
    error_message TEXT,
    next_retry_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE INDEX idx_retry_attempts_run_id ON retry_attempts(run_id);
CREATE INDEX idx_retry_attempts_status ON retry_attempts(status);
```

## Repositories to Create

### 1. RunRepository
- CRUD operations for runs
- Query by status, date range
- Update run status and timestamps
- Get run statistics

### 2. StrategyRepository
- CRUD operations for strategies
- Query by run, family, timeframe
- Get strategy configurations
- List strategies by criteria

### 3. ArtifactRepository
- CRUD operations for artifacts
- Query by run, type
- Get artifact metadata
- List artifacts for export

### 4. BacktestResultRepository
- CRUD operations for backtest results
- Query by run, strategy, pair
- Aggregate metrics across results
- Get best/worst performing strategies

### 5. MetricRepository
- CRUD operations for metrics
- Query by run, name, time range
- Aggregate metric values
- Get metric history

### 6. RunLogRepository
- CRUD operations for run logs
- Query by run, level, stage
- Get recent logs
- Paginate log results

### 7. AuditLogRepository
- CRUD operations for audit entries
- Query by entity, action, date range
- Get audit trail for entity
- Generate audit reports

### 8. RetryAttemptRepository
- CRUD operations for retry attempts
- Query by run, status
- Get pending retries
- Update retry status

## Routers to Create

### 1. runs.py
- `POST /api/v1/runs` - Create new run
- `GET /api/v1/runs` - List runs with pagination
- `GET /api/v1/runs/{id}` - Get run details
- `PUT /api/v1/runs/{id}` - Update run
- `DELETE /api/v1/runs/{id}` - Delete run
- `POST /api/v1/runs/{id}/cancel` - Cancel run
- `GET /api/v1/runs/{id}/logs` - Get run logs
- `GET /api/v1/runs/{id}/metrics` - Get run metrics

### 2. strategies.py
- `GET /api/v1/strategies` - List strategies
- `GET /api/v1/strategies/{id}` - Get strategy details
- `GET /api/v1/runs/{run_id}/strategies` - Get strategies for run
- `POST /api/v1/strategies/{id}/export` - Export strategy

### 3. artifacts.py
- `GET /api/v1/artifacts` - List artifacts
- `GET /api/v1/artifacts/{id}` - Get artifact details
- `GET /api/v1/runs/{run_id}/artifacts` - Get artifacts for run
- `GET /api/v1/artifacts/{id}/download` - Download artifact file

### 4. backtest_results.py
- `GET /api/v1/backtest-results` - List backtest results
- `GET /api/v1/backtest-results/{id}` - Get backtest details
- `GET /api/v1/runs/{run_id}/backtest-results` - Get results for run
- `GET /api/v1/strategies/{strategy_id}/backtest-results` - Get results for strategy

### 5. metrics.py
- `GET /api/v1/metrics` - List metrics
- `GET /api/v1/runs/{run_id}/metrics` - Get metrics for run
- `GET /api/v1/metrics/aggregated` - Get aggregated metrics

### 6. audit.py
- `GET /api/v1/audit` - List audit entries
- `GET /api/v1/audit/{entity_type}/{entity_id}` - Get audit trail for entity

## Pydantic Schemas to Create

### Request Schemas
- `RunCreateRequest` - Create run input
- `RunUpdateRequest` - Update run input
- `StrategyExportRequest` - Export strategy options

### Response Schemas
- `RunResponse` - Run details
- `RunListResponse` - Paginated run list
- `StrategyResponse` - Strategy details
- `ArtifactResponse` - Artifact details
- `BacktestResultResponse` - Backtest result details
- `MetricResponse` - Metric details
- `AuditLogResponse` - Audit entry details

### Internal Schemas
- `RunModel` - Internal run data model
- `StrategyModel` - Internal strategy data model
- `BacktestResultModel` - Internal backtest result model

## Test Strategy

### Repository Tests
- Use in-memory SQLite for isolation
- Test CRUD operations
- Test query methods
- Test transaction rollback on errors
- Test foreign key constraints

### API Tests
- Use FastAPI TestClient
- Test all endpoints
- Test request validation
- Test response schemas
- Test error handling
- Test authentication (if added)

### Integration Tests
- Test repository + API integration
- Test end-to-end workflows
- Test concurrent operations
- Test data consistency

### Seed Data
- Create sample runs
- Create sample strategies
- Create sample backtest results
- Use for development and testing

## File Structure

```
backend/
├── app/
│   ├── db/
│   │   ├── sqlite.py (existing)
│   │   ├── migrations.py (part 02 - extend)
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── run_repository.py
│   │       ├── strategy_repository.py
│   │       ├── artifact_repository.py
│   │       ├── backtest_result_repository.py
│   │       ├── metric_repository.py
│   │       ├── run_log_repository.py
│   │       ├── audit_log_repository.py
│   │       └── retry_attempt_repository.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── app_meta.py (existing)
│   │   ├── system_events.py (existing)
│   │   ├── local_settings.py (existing)
│   │   ├── run.py
│   │   ├── strategy.py
│   │   ├── artifact.py
│   │   ├── backtest_result.py
│   │   ├── metric.py
│   │   ├── run_log.py
│   │   ├── audit_log.py
│   │   └── retry_attempt.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── run.py
│   │   ├── strategy.py
│   │   ├── artifact.py
│   │   ├── backtest_result.py
│   │   ├── metric.py
│   │   ├── audit.py
│   │   └── common.py
│   ├── api/
│   │   ├── v1/
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── system.py (existing)
│   │   │   │   ├── health.py (existing)
│   │   │   │   ├── settings.py (existing)
│   │   │   │   ├── runs.py
│   │   │   │   ├── strategies.py
│   │   │   │   ├── artifacts.py
│   │   │   │   ├── backtest_results.py
│   │   │   │   ├── metrics.py
│   │   │   │   └── audit.py
│   │   │   └── __init__.py
│   │   └── __init__.py (existing)
│   └── services/
│       ├── system_service.py (existing)
│       └── (no new services in Part 03 - repositories handle logic)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_repositories/
    │   ├── __init__.py
    │   ├── test_run_repository.py
    │   ├── test_strategy_repository.py
    │   ├── test_artifact_repository.py
    │   └── ...
    ├── test_api/
    │   ├── __init__.py
    │   ├── test_runs.py
    │   ├── test_strategies.py
    │   └── ...
    └── test_migrations.py
```

## Risks and Safeguards

### Risk 1: Data Loss
- **Risk:** Accidental deletion of runs or strategies
- **Safeguard:** Use foreign key ON DELETE CASCADE carefully, add soft delete option
- **Safeguard:** Implement backup before destructive operations
- **Safeguard:** Require confirmation for delete operations

### Risk 2: Schema Migrations
- **Risk:** Migration failures corrupting database
- **Safeguard:** Test migrations on copy of database
- **Safeguard:** Add migration version tracking
- **Safeguard:** Provide rollback capability
- **Safeguard:** Backup database before running migrations

### Risk 3: Concurrent Access
- **Risk:** Race conditions in concurrent operations
- **Safeguard:** Use SQLite write-ahead mode (WAL)
- **Safeguard:** Implement proper transaction isolation
- **Safeguard:** Add retry logic for lock contention

### Risk 4: Secrets Exposure
- **Risk:** Secrets leaked through API responses or logs
- **Safeguard:** Use Pydantic SecretStr for sensitive fields
- **Safeguard:** Never include secrets in response schemas
- **Safeguard:** Sanitize logs to remove secrets
- **Safeguard:** Audit all API responses for secret leakage

### Risk 5: Performance Degradation
- **Risk:** Large datasets causing slow queries
- **Safeguard:** Add appropriate indexes
- **Safeguard:** Implement pagination for list endpoints
- **Safeguard:** Add query result caching where appropriate
- **Safeguard:** Monitor query performance

### Risk 6: Data Integrity
- **Risk:** Invalid data corrupting system state
- **Safeguard:** Use Pydantic validation for all inputs
- **Safeguard:** Add database constraints (NOT NULL, CHECK, FOREIGN KEY)
- **Safeguard:** Validate foreign key relationships
- **Safeguard:** Add data consistency checks

## Success Criteria

Part 03 is complete when:

1. ✅ All 8 new tables are created with proper schema
2. ✅ All 8 repositories are implemented with full CRUD
3. ✅ All Pydantic schemas are defined and validated
4. ✅ All API routers are implemented and tested
5. ✅ Repository tests achieve >80% coverage
6. ✅ API tests achieve >80% coverage
7. ✅ Seed data is available for development
8. ✅ Documentation is updated
9. ✅ No Freqtrade execution logic is added
10. ✅ No AI/Ollama strategy logic is added
11. ✅ No Discord sending logic is added
12. ✅ Secrets are never exposed in any API response

## Next Steps After Part 03

Part 04 will build on this foundation to:
- Implement AutoQuant pipeline orchestration
- Add Freqtrade integration for backtests
- Add Ollama integration for strategy design
- Implement decision engine logic
- Add Discord notification integration
- Build complete UI workflows

## Dependencies

Part 03 depends on:
- Part 01 foundation documents (read and understood)
- Part 02 project setup (complete and verified)
- Existing database infrastructure (sqlite.py, migrations.py)
- Existing API infrastructure (main.py, config.py)

Part 03 does not depend on:
- Freqtrade installation
- Ollama installation
- Discord bot setup
- External API keys
