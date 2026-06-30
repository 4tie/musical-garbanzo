"""
Tests for MetricsRepository.
"""
import pytest

from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import (
    MetricSnapshotCreate,
    PairResultCreate,
    TradeSummaryCreate,
)
from app.db.sqlite import get_connection


@pytest.fixture
def metrics_repo():
    """Create a MetricsRepository instance."""
    return MetricsRepository()


@pytest.fixture
def clean_db():
    """Clean the metrics tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM trade_summaries")
    conn.execute("DELETE FROM pair_results")
    conn.execute("DELETE FROM metrics_snapshots")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM trade_summaries")
    conn.execute("DELETE FROM pair_results")
    conn.execute("DELETE FROM metrics_snapshots")
    conn.commit()
    conn.close()


class TestMetricsRepository:
    """Test MetricsRepository operations."""
    
    def test_create_metric_snapshot(self, metrics_repo, clean_db):
        """Test creating a metric snapshot."""
        data = MetricSnapshotCreate(
            run_id="run-123",
            raw_json={"profit": 100, "trades": 50},
        )
        
        snapshot = metrics_repo.create_metric_snapshot(data)
        
        assert snapshot is not None
        assert snapshot["run_id"] == "run-123"
        assert snapshot["raw_json"] == {"profit": 100, "trades": 50}
        assert snapshot["id"] is not None
    
    def test_list_metric_snapshots(self, metrics_repo, clean_db):
        """Test listing metric snapshots."""
        metrics_repo.create_metric_snapshot(
            MetricSnapshotCreate(run_id="run-123", raw_json={"profit": 100})
        )
        metrics_repo.create_metric_snapshot(
            MetricSnapshotCreate(run_id="run-123", raw_json={"profit": 150})
        )
        
        snapshots = metrics_repo.list_metric_snapshots("run-123")
        
        assert len(snapshots) == 2
    
    def test_get_latest_metric_snapshot(self, metrics_repo, clean_db):
        """Test getting the latest metric snapshot."""
        metrics_repo.create_metric_snapshot(
            MetricSnapshotCreate(run_id="run-123", raw_json={"profit": 100})
        )
        metrics_repo.create_metric_snapshot(
            MetricSnapshotCreate(run_id="run-123", raw_json={"profit": 150})
        )
        
        latest = metrics_repo.get_latest_metric_snapshot("run-123")
        
        assert latest is not None
        assert latest["raw_json"]["profit"] == 150
    
    def test_get_latest_metric_snapshot_none(self, metrics_repo, clean_db):
        """Test getting latest snapshot when none exists."""
        latest = metrics_repo.get_latest_metric_snapshot("run-123")
        assert latest is None
    
    def test_create_pair_result(self, metrics_repo, clean_db):
        """Test creating a pair result."""
        data = PairResultCreate(
            run_id="run-123",
            pair="BTC/USDT",
            raw_json={"profit": 50},
        )
        
        result = metrics_repo.create_pair_result(data)
        
        assert result is not None
        assert result["run_id"] == "run-123"
        assert result["pair"] == "BTC/USDT"
        assert result["raw_json"] == {"profit": 50}
    
    def test_list_pair_results(self, metrics_repo, clean_db):
        """Test listing pair results."""
        metrics_repo.create_pair_result(
            PairResultCreate(run_id="run-123", pair="BTC/USDT", raw_json={"profit": 50})
        )
        metrics_repo.create_pair_result(
            PairResultCreate(run_id="run-123", pair="ETH/USDT", raw_json={"profit": 30})
        )
        
        results = metrics_repo.list_pair_results("run-123")
        
        assert len(results) == 2
    
    def test_create_trade_summary(self, metrics_repo, clean_db):
        """Test creating a trade summary."""
        data = TradeSummaryCreate(
            run_id="run-123",
            total_trades=50,
            wins=30,
            losses=20,
            draws=0,
        )
        
        summary = metrics_repo.create_trade_summary(data)
        
        assert summary is not None
        assert summary["run_id"] == "run-123"
        assert summary["total_trades"] == 50
        assert summary["wins"] == 30
        assert summary["losses"] == 20
        assert summary["draws"] == 0
    
    def test_get_trade_summary_by_run(self, metrics_repo, clean_db):
        """Test getting trade summary by run ID."""
        metrics_repo.create_trade_summary(
            TradeSummaryCreate(run_id="run-123", total_trades=50, wins=30, losses=20)
        )
        
        summary = metrics_repo.get_trade_summary_by_run("run-123")
        
        assert summary is not None
        assert summary["run_id"] == "run-123"
        assert summary["total_trades"] == 50

        same_summary = metrics_repo.get_trade_summary("run-123")
        assert same_summary["id"] == summary["id"]
    
    def test_get_trade_summary_by_run_none(self, metrics_repo, clean_db):
        """Test getting trade summary when none exists."""
        summary = metrics_repo.get_trade_summary_by_run("run-123")
        assert summary is None
    
    def test_json_roundtrip(self, metrics_repo, clean_db):
        """Test that JSON data serializes/deserializes correctly."""
        raw_data = {"profit": 100, "trades": 50, "pairs": {"BTC": 50, "ETH": 50}}
        
        snapshot = metrics_repo.create_metric_snapshot(
            MetricSnapshotCreate(run_id="run-123", raw_json=raw_data)
        )
        
        assert snapshot["raw_json"] == raw_data
        assert isinstance(snapshot["raw_json"], dict)
