"""
Tests for RunLogRepository, RetryHistoryRepository, and AuditLogRepository.
"""
import pytest

from app.repositories.logs import RunLogRepository
from app.repositories.retry_history import RetryHistoryRepository
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.logs import RunLogCreate
from app.schemas.retry_history import RetryHistoryCreate
from app.schemas.audit_logs import AuditLogCreate
from app.db.sqlite import get_connection


@pytest.fixture
def log_repo():
    """Create a RunLogRepository instance."""
    return RunLogRepository()


@pytest.fixture
def retry_repo():
    """Create a RetryHistoryRepository instance."""
    return RetryHistoryRepository()


@pytest.fixture
def audit_repo():
    """Create an AuditLogRepository instance."""
    return AuditLogRepository()


@pytest.fixture
def clean_db():
    """Clean the logs, retry_history, and audit_logs tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM retry_history")
    conn.execute("DELETE FROM run_logs")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM retry_history")
    conn.execute("DELETE FROM run_logs")
    conn.commit()
    conn.close()


class TestRunLogRepository:
    """Test RunLogRepository operations."""
    
    def test_add_log(self, log_repo, clean_db):
        """Test adding a log entry."""
        log = log_repo.add_log(
            run_id="run-123",
            level="info",
            source="system",
            message="Test message",
        )
        
        assert log is not None
        assert log["run_id"] == "run-123"
        assert log["level"] == "info"
        assert log["source"] == "system"
        assert log["message"] == "Test message"
    
    def test_add_log_with_details(self, log_repo, clean_db):
        """Test adding a log entry with details."""
        log = log_repo.add_log(
            run_id="run-123",
            level="info",
            source="system",
            message="Test message",
            details={"key": "value"},
        )
        
        assert log is not None
        assert log["details"] == {"key": "value"}
    
    def test_list_logs(self, log_repo, clean_db):
        """Test listing logs."""
        log_repo.add_log(run_id="run-123", level="info", source="system", message="Message 1")
        log_repo.add_log(run_id="run-123", level="warning", source="system", message="Message 2")
        
        logs = log_repo.list_logs(run_id="run-123")
        
        assert len(logs) == 2
    
    def test_list_logs_with_level_filter(self, log_repo, clean_db):
        """Test listing logs with level filter."""
        log_repo.add_log(run_id="run-123", level="info", source="system", message="Message 1")
        log_repo.add_log(run_id="run-123", level="error", source="system", message="Message 2")
        
        logs = log_repo.list_logs(run_id="run-123", level="error")
        
        assert len(logs) == 1
        assert logs[0]["level"] == "error"

    def test_critical_log_level_allowed(self, log_repo, clean_db):
        """Test that critical log level is accepted."""
        log = log_repo.add_log(
            run_id="run-123",
            level="critical",
            source="system",
            message="Critical failure marker",
        )

        assert log["level"] == "critical"
    
    def test_list_logs_with_stage_filter(self, log_repo, clean_db):
        """Test listing logs with stage_key filter."""
        log_repo.add_log(run_id="run-123", level="info", source="system", message="Message 1", stage_key="generate")
        log_repo.add_log(run_id="run-123", level="info", source="system", message="Message 2", stage_key="backtest")
        
        logs = log_repo.list_logs(run_id="run-123", stage_key="generate")
        
        assert len(logs) == 1
        assert logs[0]["stage_key"] == "generate"
    
    def test_secret_like_details_sanitized(self, log_repo, clean_db):
        """Test that secret-like values are sanitized."""
        log = log_repo.add_log(
            run_id="run-123",
            level="info",
            source="system",
            message="Test message",
            details={
                "api_key": "secret123",
                "token": "token456",
                "normal_key": "normal_value",
            },
        )
        
        assert log["details"]["api_key"] == "[REDACTED]"
        assert log["details"]["token"] == "[REDACTED]"
        assert log["details"]["normal_key"] == "normal_value"
    
    def test_nested_secret_sanitized(self, log_repo, clean_db):
        """Test that nested secret-like values are sanitized."""
        log = log_repo.add_log(
            run_id="run-123",
            level="info",
            source="system",
            message="Test message",
            details={
                "config": {
                    "api_key": "secret123",
                    "other": "value",
                }
            },
        )
        
        assert log["details"]["config"]["api_key"] == "[REDACTED]"
        assert log["details"]["config"]["other"] == "value"
    
    def test_invalid_level_rejected(self, log_repo, clean_db):
        """Test that invalid log level is rejected."""
        with pytest.raises(ValueError):
            log_repo.add_log(
                run_id="run-123",
                level="invalid",
                source="system",
                message="Test message",
            )


class TestRetryHistoryRepository:
    """Test RetryHistoryRepository operations."""
    
    def test_create_retry_entry(self, retry_repo, clean_db):
        """Test creating a retry entry."""
        data = RetryHistoryCreate(
            run_id="run-123",
            parent_run_id="run-122",
            stage_key="backtest",
            status="proposed",
            error_message="Strategy failed",
            proposed_fix={"fix": "correct syntax"},
        )
        
        entry = retry_repo.create_retry_entry(data)
        
        assert entry is not None
        assert entry["run_id"] == "run-123"
        assert entry["parent_run_id"] == "run-122"
        assert entry["stage_key"] == "backtest"
        assert entry["status"] == "proposed"
        assert entry["error_message"] == "Strategy failed"
        assert entry["proposed_fix"] == {"fix": "correct syntax"}
    
    def test_list_retry_history(self, retry_repo, clean_db):
        """Test listing retry history."""
        retry_repo.create_retry_entry(
            RetryHistoryCreate(run_id="run-123", status="proposed", error_message="Error 1")
        )
        retry_repo.create_retry_entry(
            RetryHistoryCreate(run_id="run-123", status="applied", error_message="Error 2")
        )
        
        history = retry_repo.list_retry_history("run-123")
        
        assert len(history) == 2
    
    def test_complete_retry(self, retry_repo, clean_db):
        """Test completing a retry entry."""
        entry = retry_repo.create_retry_entry(
            RetryHistoryCreate(run_id="run-123", status="proposed", error_message="Error")
        )
        
        completed = retry_repo.complete_retry(
            retry_id=entry["id"],
            status="applied",
            applied_fix={"fix": "applied"},
        )
        
        assert completed["status"] == "applied"
        assert completed["applied_fix"] == {"fix": "applied"}
        assert completed["completed_at"] is not None
    
    def test_complete_retry_with_error(self, retry_repo, clean_db):
        """Test completing a retry entry with error."""
        entry = retry_repo.create_retry_entry(
            RetryHistoryCreate(run_id="run-123", status="proposed", error_message="Error")
        )
        
        completed = retry_repo.complete_retry(
            retry_id=entry["id"],
            status="failed",
            error_message="Fix failed",
        )
        
        assert completed["status"] == "failed"
        assert completed["error_message"] == "Fix failed"
    
    def test_complete_retry_not_found(self, retry_repo, clean_db):
        """Test completing a non-existent retry entry."""
        with pytest.raises(ValueError):
            retry_repo.complete_retry(
                retry_id="non-existent-id",
                status="applied",
            )
    
    def test_invalid_status_rejected(self, retry_repo, clean_db):
        """Test that invalid retry status is rejected."""
        data = RetryHistoryCreate(
            run_id="run-123",
            status="invalid",
        )
        
        with pytest.raises(ValueError):
            retry_repo.create_retry_entry(data)


class TestAuditLogRepository:
    """Test AuditLogRepository operations."""
    
    def test_create_audit_log(self, audit_repo, clean_db):
        """Test creating an audit log entry."""
        data = AuditLogCreate(
            run_id="run-123",
            actor="ai_assistant",
            action_type="create",
            target_type="strategy",
            target_id="strat-123",
            before=None,
            after={"name": "MyStrategy"},
            changed_files=["strategy.py"],
            approved=True,
            notes="Generated by AI",
        )
        
        log = audit_repo.create_audit_log(data)
        
        assert log is not None
        assert log["run_id"] == "run-123"
        assert log["actor"] == "ai_assistant"
        assert log["action_type"] == "create"
        assert log["target_type"] == "strategy"
        assert log["after"] == {"name": "MyStrategy"}
        assert log["changed_files"] == ["strategy.py"]
        assert log["approved"] is True
    
    def test_list_audit_logs(self, audit_repo, clean_db):
        """Test listing audit logs."""
        audit_repo.create_audit_log(
            AuditLogCreate(actor="ai_assistant", action_type="create", target_type="strategy")
        )
        audit_repo.create_audit_log(
            AuditLogCreate(actor="user", action_type="update", target_type="strategy")
        )
        
        logs = audit_repo.list_audit_logs()
        
        assert len(logs) == 2
    
    def test_list_audit_logs_with_run_filter(self, audit_repo, clean_db):
        """Test listing audit logs with run_id filter."""
        audit_repo.create_audit_log(
            AuditLogCreate(run_id="run-1", actor="ai_assistant", action_type="create")
        )
        audit_repo.create_audit_log(
            AuditLogCreate(run_id="run-2", actor="ai_assistant", action_type="create")
        )
        
        logs = audit_repo.list_audit_logs(run_id="run-1")
        
        assert len(logs) == 1
        assert logs[0]["run_id"] == "run-1"
    
    def test_list_audit_logs_with_action_filter(self, audit_repo, clean_db):
        """Test listing audit logs with action_type filter."""
        audit_repo.create_audit_log(
            AuditLogCreate(actor="ai_assistant", action_type="create", target_type="strategy")
        )
        audit_repo.create_audit_log(
            AuditLogCreate(actor="ai_assistant", action_type="update", target_type="strategy")
        )
        
        logs = audit_repo.list_audit_logs(action_type="create")
        
        assert len(logs) == 1
        assert logs[0]["action_type"] == "create"

    def test_ai_role_actors_allowed(self, audit_repo, clean_db):
        """Test all HER AI audit actor roles are accepted."""
        for actor in ("ai_assistant", "ai_strategy_designer", "ai_repair_agent"):
            log = audit_repo.create_audit_log(
                AuditLogCreate(actor=actor, action_type="role_check")
            )
            assert log["actor"] == actor
    
    def test_invalid_actor_rejected(self, audit_repo, clean_db):
        """Test that invalid actor is rejected."""
        data = AuditLogCreate(
            actor="invalid",
            action_type="create",
        )
        
        with pytest.raises(ValueError):
            audit_repo.create_audit_log(data)

    def test_secret_like_audit_json_sanitized(self, audit_repo, clean_db):
        """Test that secret-like values in audit JSON are sanitized."""
        log = audit_repo.create_audit_log(
            AuditLogCreate(
                actor="ai_assistant",
                action_type="update",
                before={"config": {"api_key": "secret123"}},
                after={"changes": [{"private_key": "key123"}, {"safe": "value"}]},
            )
        )

        assert log["before"]["config"]["api_key"] == "[REDACTED]"
        assert log["after"]["changes"][0]["private_key"] == "[REDACTED]"
        assert log["after"]["changes"][1]["safe"] == "value"
    
    def test_approved_bool_conversion(self, audit_repo, clean_db):
        """Test that approved is converted from int to bool."""
        log = audit_repo.create_audit_log(
            AuditLogCreate(actor="ai_assistant", action_type="create", approved=True)
        )
        
        assert log["approved"] is True
        assert isinstance(log["approved"], bool)
