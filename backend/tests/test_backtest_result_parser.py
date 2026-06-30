"""
Tests for backtest result parser persistence orchestration.
"""
import json
from pathlib import Path

import pytest

from app.db.sqlite import get_connection
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.logs import RunLogRepository
from app.repositories.metrics import MetricsRepository
from app.services.backtest_result_parser import BacktestResultParser


@pytest.fixture
def clean_parser_db():
    """Clean parser-related tables before and after each test."""
    conn = get_connection()
    for table in ("audit_logs", "run_logs", "artifacts", "trade_summaries", "pair_results", "metrics_snapshots"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    yield
    conn = get_connection()
    for table in ("audit_logs", "run_logs", "artifacts", "trade_summaries", "pair_results", "metrics_snapshots"):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


def make_parser(tmp_path: Path) -> BacktestResultParser:
    """Build parser rooted in a temp project directory."""
    return BacktestResultParser(project_root=tmp_path)


def write_fixture(path: Path, profit: float = 8.0, eth_profit: float = 2.0) -> Path:
    """Write a small structured backtest result fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "strategy": {
            "HERSmokeStrategy": {
                "profit_total_abs": profit + eth_profit,
                "profit_factor": 1.4,
                "max_drawdown_pct": 12.5,
                "total_trades": 3,
                "wins": 2,
                "losses": 1,
                "draws": 0,
                "avg_win": 6.0,
                "avg_loss": -2.0,
                "results_per_pair": [
                    {
                        "pair": "BTC/USDT",
                        "trades": 2,
                        "profit_total_abs": profit,
                        "profit_factor": 1.6,
                        "max_drawdown": 4.0,
                        "wins": 1,
                        "losses": 1,
                        "draws": 0,
                    },
                    {
                        "pair": "ETH/USDT",
                        "trades": 1,
                        "profit_total_abs": eth_profit,
                        "profit_factor": 2.0,
                        "max_drawdown": 1.0,
                        "wins": 1,
                        "losses": 0,
                        "draws": 0,
                    },
                ],
            }
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_parse_run_missing_outputs_returns_controlled_failure(tmp_path, clean_parser_db):
    """Missing output files return a controlled failure and audit/log evidence."""
    result = make_parser(tmp_path).parse_run("missing-run")

    assert result.success is False
    assert result.discovery is not None
    assert "missing_backtest_file" in {flag.code for flag in result.quality_report.flags}
    assert result.saved_records["quality_audit"]["action_type"] == "backtest_result_quality"
    assert AuditLogRepository().list_audit_logs(run_id="missing-run")[0]["approved"] is False
    assert RunLogRepository().list_logs(run_id="missing-run")


def test_parse_from_paths_saves_metrics(tmp_path, clean_parser_db):
    """Explicit path parsing saves a metric snapshot."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    result = make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    metrics = MetricsRepository().list_metric_snapshots("run-123")
    assert result.success is True
    assert len(metrics) == 1
    assert metrics[0]["net_profit"] == 10.0
    assert metrics[0]["profit_factor"] == 1.4
    assert metrics[0]["trade_count"] == 3


def test_pair_results_saved_upserted(tmp_path, clean_parser_db):
    """Pair results are upserted by run/pair on repeated parses."""
    result_file = write_fixture(tmp_path / "backtest-result.json", profit=8.0)
    parser = make_parser(tmp_path)

    parser.parse_from_paths("run-123", [str(result_file)])
    write_fixture(result_file, profit=20.0)
    parser.parse_from_paths("run-123", [str(result_file)])

    pairs = MetricsRepository().list_pair_results("run-123")
    btc = next(pair for pair in pairs if pair["pair"] == "BTC/USDT")
    assert len(pairs) == 2
    assert btc["net_profit"] == 20.0


def test_trade_summary_saved_replaced(tmp_path, clean_parser_db):
    """Trade summaries are replaced rather than duplicated."""
    result_file = write_fixture(tmp_path / "backtest-result.json")
    parser = make_parser(tmp_path)

    parser.parse_from_paths("run-123", [str(result_file)])
    parser.parse_from_paths("run-123", [str(result_file)])

    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM trade_summaries WHERE run_id = ?", ("run-123",)).fetchone()[0]
    conn.close()
    summary = MetricsRepository().get_trade_summary("run-123")

    assert count == 1
    assert summary["total_trades"] == 3
    assert summary["best_pair"] == "BTC/USDT"


def test_normalized_artifact_written(tmp_path, clean_parser_db):
    """Parser writes the normalized result artifact."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    result = make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    normalized_path = Path(result.normalized_result_path)
    assert normalized_path.exists()
    data = json.loads(normalized_path.read_text(encoding="utf-8"))
    assert data["run_id"] == "run-123"
    assert data["metrics"]["profit_factor"] == 1.4
    assert data["quality_flags"]


def test_artifact_registered(tmp_path, clean_parser_db):
    """Normalized result artifact is registered as metrics_json."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    result = make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    artifacts = ArtifactRepository().list_artifacts(run_id="run-123", artifact_type="metrics_json")
    assert len(artifacts) == 1
    assert artifacts[0]["description"] == "Normalized parsed backtest result"
    assert artifacts[0]["file_path"] == result.normalized_result_path


def test_logs_written(tmp_path, clean_parser_db):
    """Parser writes run logs."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    logs = RunLogRepository().list_logs(run_id="run-123")
    assert any(log["source"] == "backtest_result_parser" for log in logs)


def test_audit_log_written(tmp_path, clean_parser_db):
    """Parser writes audit logs without approval semantics."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    audits = AuditLogRepository().list_audit_logs(run_id="run-123")
    action_types = {audit["action_type"] for audit in audits}
    assert "backtest_result_parse" in action_types
    assert "backtest_result_quality" in action_types
    assert all(audit["approved"] is False for audit in audits)


def test_force_reparse_behavior(tmp_path, clean_parser_db):
    """Force reparse deletes previous metric snapshots before saving current one."""
    result_file = write_fixture(tmp_path / "backtest-result.json")
    parser = make_parser(tmp_path)

    parser.parse_from_paths("run-123", [str(result_file)])
    result = parser.parse_from_paths("run-123", [str(result_file)], force=True)

    metrics = MetricsRepository().list_metric_snapshots("run-123")
    assert len(metrics) == 1
    assert result.saved_records["deleted_metric_snapshots"] == 1


def test_raw_files_not_deleted(tmp_path, clean_parser_db):
    """Parser never deletes raw result files."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])

    assert result_file.exists()


def test_run_not_approved_or_classified(tmp_path, clean_parser_db):
    """Parser output and audits contain no final approval/classification decision."""
    result_file = write_fixture(tmp_path / "backtest-result.json")

    result = make_parser(tmp_path).parse_from_paths("run-123", [str(result_file)])
    text = result.model_dump_json()
    audits = AuditLogRepository().list_audit_logs(run_id="run-123")

    assert all(audit["approved"] is False for audit in audits)
    assert "rejected" not in text.lower()
    assert "profitable" not in text.lower()
