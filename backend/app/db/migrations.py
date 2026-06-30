"""
Database migrations for HER backend.
"""
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.db.sqlite import get_connection


def run_migrations() -> None:
    """Run all database migrations to create/update schema."""
    conn = get_connection()
    try:
        # Part 02 tables
        create_app_meta_table(conn)
        create_system_events_table(conn)
        create_local_settings_table(conn)
        
        # Part 03 backend core tables
        migrate_part_03_backend_core(conn)
        
        # Part 08 optimization tables
        migrate_part_08_optimization(conn)

        # Part 13 validation evidence tables
        migrate_part_13_validation(conn)
        
        conn.commit()
    finally:
        conn.close()


def create_app_meta_table(conn: sqlite3.Connection) -> None:
    """Create the app_meta table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


def create_system_events_table(conn: sqlite3.Connection) -> None:
    """Create the system_events table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_events (
            id TEXT PRIMARY KEY,
            level TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            details_json TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create indexes
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_events_created_at 
        ON system_events(created_at)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_events_level 
        ON system_events(level)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_system_events_source 
        ON system_events(source)
    """)


def create_local_settings_table(conn: sqlite3.Connection) -> None:
    """Create the local_settings table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS local_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            is_secret INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)


def upsert_app_meta(key: str, value: str) -> None:
    """Insert or update an app_meta entry."""
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("""
            INSERT INTO app_meta (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value, now))
        conn.commit()
    finally:
        conn.close()


def get_app_meta(key: str) -> Optional[str]:
    """Get an app_meta value by key."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT value FROM app_meta WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def insert_system_event(
    level: str,
    source: str,
    message: str,
    details: Optional[dict] = None
) -> str:
    """
    Insert a system event.
    
    Args:
        level: Event level (info, warning, error, etc.)
        source: Event source (backend, frontend, etc.)
        message: Event message
        details: Optional details as dict
    
    Returns:
        The event ID
    """
    import uuid
    import json
    
    conn = get_connection()
    try:
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        details_json = json.dumps(details) if details else None
        
        conn.execute("""
            INSERT INTO system_events (id, level, source, message, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_id, level, source, message, details_json, now))
        conn.commit()
        return event_id
    finally:
        conn.close()


def get_recent_system_events(limit: int = 50) -> list:
    """
    Get recent system events.
    
    Args:
        limit: Maximum number of events to return
    
    Returns:
        List of system event dicts
    """
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT id, level, source, message, details_json, created_at
            FROM system_events
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        events = []
        for row in cursor.fetchall():
            event = dict(row)
            # Parse details_json if present
            if event["details_json"]:
                import json
                event["details"] = json.loads(event["details_json"])
            del event["details_json"]
            events.append(event)
        
        return events
    finally:
        conn.close()


def upsert_local_setting(key: str, value: dict, is_secret: bool = False) -> None:
    """
    Insert or update a local setting.
    
    Args:
        key: Setting key
        value: Setting value as dict
        is_secret: Whether the value contains secrets
    """
    import json
    
    conn = get_connection()
    try:
        now = datetime.now(timezone.utc).isoformat()
        value_json = json.dumps(value)
        
        conn.execute("""
            INSERT INTO local_settings (key, value_json, is_secret, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                is_secret = excluded.is_secret,
                updated_at = excluded.updated_at
        """, (key, value_json, 1 if is_secret else 0, now))
        conn.commit()
    finally:
        conn.close()


def get_local_setting(key: str) -> Optional[dict]:
    """
    Get a local setting by key.
    
    Args:
        key: Setting key
    
    Returns:
        Setting value as dict, or None if not found
    """
    import json
    
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT value_json, is_secret 
            FROM local_settings 
            WHERE key = ?
        """, (key,))
        
        row = cursor.fetchone()
        if row:
            return json.loads(row["value_json"])
        return None
    finally:
        conn.close()


def get_public_local_settings() -> dict:
    """
    Get all non-secret local settings.
    
    Returns:
        Dict of non-secret settings
    """
    import json
    
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT key, value_json 
            FROM local_settings 
            WHERE is_secret = 0
        """)
        
        settings = {}
        for row in cursor.fetchall():
            settings[row["key"]] = json.loads(row["value_json"])
        
        return settings
    finally:
        conn.close()


def migrate_part_03_backend_core(conn: sqlite3.Connection) -> None:
    """
    Create all Part 03 backend core tables and indexes.
    
    This migration is idempotent - it uses CREATE TABLE IF NOT EXISTS
    and CREATE INDEX IF NOT EXISTS to ensure it can be run multiple times.
    
    Args:
        conn: SQLite connection
    """
    # Create tables
    create_runs_table(conn)
    create_run_stages_table(conn)
    create_strategies_table(conn)
    create_strategy_versions_table(conn)
    create_artifacts_table(conn)
    create_metrics_snapshots_table(conn)
    create_pair_results_table(conn)
    create_trade_summaries_table(conn)
    create_run_logs_table(conn)
    create_retry_history_table(conn)
    create_audit_logs_table(conn)
    create_decision_results_table(conn)
    
    # Create indexes
    create_part_03_indexes(conn)


def create_runs_table(conn: sqlite3.Connection) -> None:
    """Create the runs table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            classification TEXT,
            strategy_id TEXT,
            parent_run_id TEXT,
            exchange TEXT,
            quote_currency TEXT,
            trading_mode TEXT,
            timeframe TEXT,
            pairs_json TEXT,
            timerange TEXT,
            risk_profile TEXT,
            analysis_depth TEXT,
            is_demo INTEGER NOT NULL DEFAULT 0,
            failure_reason TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT
        )
    """)


def create_run_stages_table(conn: sqlite3.Connection) -> None:
    """Create the run_stages table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_stages (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            stage_key TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            duration_ms INTEGER,
            input_json TEXT,
            output_json TEXT,
            error_json TEXT,
            logs_summary TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(run_id, stage_key)
        )
    """)


def create_strategies_table(conn: sqlite3.Connection) -> None:
    """Create the strategies table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class_name TEXT,
            source_type TEXT NOT NULL,
            current_version_id TEXT,
            timeframe TEXT,
            direction TEXT,
            file_path TEXT,
            params_path TEXT,
            status TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


def create_strategy_versions_table(conn: sqlite3.Connection) -> None:
    """Create the strategy_versions table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS strategy_versions (
            id TEXT PRIMARY KEY,
            strategy_id TEXT NOT NULL,
            version_number INTEGER NOT NULL,
            py_path TEXT,
            json_path TEXT,
            spec_json TEXT,
            params_json TEXT,
            code_hash TEXT,
            created_from_run_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(strategy_id, version_number)
        )
    """)


def create_artifacts_table(conn: sqlite3.Connection) -> None:
    """Create the artifacts table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS artifacts (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            strategy_id TEXT,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT,
            size_bytes INTEGER,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_metrics_snapshots_table(conn: sqlite3.Connection) -> None:
    """Create the metrics_snapshots table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics_snapshots (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            stage_key TEXT,
            net_profit REAL,
            profit_factor REAL,
            max_drawdown REAL,
            sharpe REAL,
            calmar REAL,
            win_rate REAL,
            trade_count INTEGER,
            expectancy REAL,
            avg_win REAL,
            avg_loss REAL,
            raw_json TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_pair_results_table(conn: sqlite3.Connection) -> None:
    """Create the pair_results table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pair_results (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            net_profit REAL,
            profit_factor REAL,
            max_drawdown REAL,
            trade_count INTEGER,
            win_rate REAL,
            expectancy REAL,
            raw_json TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(run_id, pair)
        )
    """)


def create_trade_summaries_table(conn: sqlite3.Connection) -> None:
    """Create the trade_summaries table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_summaries (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            total_trades INTEGER,
            wins INTEGER,
            losses INTEGER,
            draws INTEGER,
            avg_duration TEXT,
            best_pair TEXT,
            worst_pair TEXT,
            raw_json TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_run_logs_table(conn: sqlite3.Connection) -> None:
    """Create the run_logs table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS run_logs (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            stage_key TEXT,
            level TEXT NOT NULL,
            source TEXT NOT NULL,
            message TEXT NOT NULL,
            details_json TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_retry_history_table(conn: sqlite3.Connection) -> None:
    """Create the retry_history table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retry_history (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            parent_run_id TEXT,
            attempt_number INTEGER NOT NULL DEFAULT 1,
            reason TEXT,
            stage_key TEXT,
            proposed_fix_json TEXT,
            applied_fix_json TEXT,
            status TEXT NOT NULL,
            error_message TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT
        )
    """)


def create_audit_logs_table(conn: sqlite3.Connection) -> None:
    """Create the audit_logs table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            run_id TEXT,
            action_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            target_type TEXT,
            target_id TEXT,
            before_json TEXT,
            after_json TEXT,
            changed_files_json TEXT,
            rollback_path TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_decision_results_table(conn: sqlite3.Connection) -> None:
    """Create the Part 06 decision_results table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decision_results (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            classification TEXT NOT NULL,
            confidence_score REAL,
            policy_name TEXT NOT NULL,
            risk_profile TEXT,
            timeframe TEXT,
            decision_json TEXT NOT NULL,
            gates_json TEXT,
            reasons_json TEXT,
            evidence_json TEXT,
            warnings_json TEXT,
            blocking_failures_json TEXT,
            normalized_result_artifact_path TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_part_03_indexes(conn: sqlite3.Connection) -> None:
    """Create all Part 03 indexes."""
    # Runs indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_classification ON runs(classification)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_strategy_id ON runs(strategy_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_parent_run_id ON runs(parent_run_id)")
    
    # Run stages indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_stages_run_id ON run_stages(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_stages_status ON run_stages(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_stages_order ON run_stages(order_index)")
    
    # Strategies indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_name ON strategies(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_strategies_source_type ON strategies(source_type)")
    
    # Artifacts indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_run_id ON artifacts(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_strategy_id ON artifacts(strategy_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type)")
    
    # Metrics indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_run_id ON metrics_snapshots(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pair_results_run_id ON pair_results(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_trade_summaries_run_id ON trade_summaries(run_id)")
    
    # Logs indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_logs_run_id ON run_logs(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_logs_stage_key ON run_logs(stage_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_logs_level ON run_logs(level)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_run_logs_created_at ON run_logs(created_at)")
    
    # Retry/audit indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_retry_history_run_id ON retry_history(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_retry_history_parent_run_id ON retry_history(parent_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_run_id ON audit_logs(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")

    # Decision indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_results_run_id ON decision_results(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_results_classification ON decision_results(classification)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_results_created_at ON decision_results(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_results_policy_name ON decision_results(policy_name)")

    ensure_part_03_columns(conn)


def ensure_part_03_columns(conn: sqlite3.Connection) -> None:
    """Add columns introduced during Part 03 prompt refinement."""
    ensure_column(conn, "retry_history", "attempt_number", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "retry_history", "reason", "TEXT")
    ensure_column(conn, "retry_history", "stage_key", "TEXT")

    ensure_column(conn, "audit_logs", "description", "TEXT")
    ensure_column(conn, "audit_logs", "target_type", "TEXT")
    ensure_column(conn, "audit_logs", "target_id", "TEXT")
    ensure_column(conn, "audit_logs", "rollback_path", "TEXT")
    ensure_column(conn, "audit_logs", "notes", "TEXT")


def ensure_column(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    """Add a column if the local SQLite table does not already have it."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    if column_name not in existing_columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def migrate_part_08_optimization(conn: sqlite3.Connection) -> None:
    """
    Create all Part 08 optimization tables and indexes.
    
    This migration is idempotent - it uses CREATE TABLE IF NOT EXISTS
    and CREATE INDEX IF NOT EXISTS to ensure it can be run multiple times.
    
    Args:
        conn: SQLite connection
    """
    # Create tables
    create_optimization_runs_table(conn)
    create_optimization_trials_table(conn)
    
    # Create indexes
    create_part_08_indexes(conn)


def create_optimization_runs_table(conn: sqlite3.Connection) -> None:
    """Create the optimization_runs table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS optimization_runs (
            id TEXT PRIMARY KEY,
            parent_run_id TEXT,
            baseline_run_id TEXT,
            optimized_run_id TEXT,
            strategy_name TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            pairs_json TEXT NOT NULL,
            exchange TEXT NOT NULL,
            risk_profile TEXT,
            status TEXT NOT NULL,
            result_status TEXT,
            best_trial_id TEXT,
            epochs_requested INTEGER,
            epochs_completed INTEGER,
            spaces_json TEXT,
            policy_json TEXT,
            request_json TEXT,
            comparison_json TEXT,
            report_artifact_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


def create_optimization_trials_table(conn: sqlite3.Connection) -> None:
    """Create the optimization_trials table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS optimization_trials (
            id TEXT PRIMARY KEY,
            optimization_run_id TEXT NOT NULL,
            trial_number INTEGER NOT NULL,
            status TEXT NOT NULL,
            is_best INTEGER NOT NULL DEFAULT 0,
            is_selected_for_validation INTEGER NOT NULL DEFAULT 0,
            params_json TEXT NOT NULL,
            buy_params_json TEXT,
            sell_params_json TEXT,
            roi_params_json TEXT,
            stoploss_params_json TEXT,
            trailing_params_json TEXT,
            metrics_json TEXT,
            loss_score REAL,
            profit_total REAL,
            profit_factor REAL,
            expectancy REAL,
            max_drawdown REAL,
            trade_count INTEGER,
            win_rate REAL,
            rejection_reason TEXT,
            failure_reason TEXT,
            artifact_paths_json TEXT,
            raw_trial_json TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_part_08_indexes(conn: sqlite3.Connection) -> None:
    """Create all Part 08 indexes."""
    # Optimization runs indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_runs_strategy_name ON optimization_runs(strategy_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_runs_status ON optimization_runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_runs_result_status ON optimization_runs(result_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_runs_created_at ON optimization_runs(created_at)")
    
    # Optimization trials indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_trials_run_id ON optimization_trials(optimization_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_trials_trial_number ON optimization_trials(trial_number)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_trials_is_best ON optimization_trials(is_best)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_optimization_trials_status ON optimization_trials(status)")


def migrate_part_13_validation(conn: sqlite3.Connection) -> None:
    """
    Create all Part 13 validation evidence tables and indexes.

    This migration is idempotent - it uses CREATE TABLE IF NOT EXISTS
    and CREATE INDEX IF NOT EXISTS to ensure it can be run multiple times.

    Args:
        conn: SQLite connection
    """
    create_validation_runs_table(conn)
    create_validation_evidence_table(conn)
    create_part_13_indexes(conn)


def create_validation_runs_table(conn: sqlite3.Connection) -> None:
    """Create the validation_runs table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS validation_runs (
            id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_run_id TEXT,
            strategy_name TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            pairs_json TEXT NOT NULL,
            exchange TEXT NOT NULL,
            risk_profile TEXT,
            status TEXT NOT NULL,
            decision_status TEXT,
            timerange TEXT,
            oos_timerange TEXT,
            wfo_config_json TEXT,
            policy_json TEXT,
            request_json TEXT,
            decision_json TEXT,
            summary_json TEXT,
            report_artifact_path TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)


def create_validation_evidence_table(conn: sqlite3.Connection) -> None:
    """Create the validation_evidence table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS validation_evidence (
            id TEXT PRIMARY KEY,
            validation_run_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            status TEXT NOT NULL,
            window_index INTEGER,
            timerange TEXT,
            metrics_json TEXT,
            decision_json TEXT,
            issues_json TEXT,
            warnings_json TEXT,
            artifact_paths_json TEXT,
            created_at TEXT NOT NULL
        )
    """)


def create_part_13_indexes(conn: sqlite3.Connection) -> None:
    """Create all Part 13 validation evidence indexes."""
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_runs_strategy_name ON validation_runs(strategy_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_runs_status ON validation_runs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_runs_decision_status ON validation_runs(decision_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_runs_created_at ON validation_runs(created_at)")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_evidence_run_id ON validation_evidence(validation_run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_evidence_type ON validation_evidence(evidence_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_evidence_status ON validation_evidence(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_validation_evidence_window_index ON validation_evidence(window_index)")
