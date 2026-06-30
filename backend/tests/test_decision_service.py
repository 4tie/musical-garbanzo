"""
Tests for Part 06 DecisionService.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.core.config import settings
from app.db.migrations import run_migrations
from app.db.sqlite import get_connection
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.decisions import DecisionRepository
from app.repositories.logs import RunLogRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.runs import RunRepository
from app.schemas.decisions import DecisionEvaluationRequest
from app.schemas.metrics import MetricSnapshotCreate, PairResultCreate, TradeSummaryCreate
from app.schemas.runs import RunCreate
from app.services.decision_service import DecisionService


TEST_RUN_NAME_PREFIX = "Decision Service Test"


@pytest.fixture
def clean_decision_service_state():
    """Clean rows and artifacts created by these tests."""
    run_migrations()
    _cleanup_test_runs()
    yield
    _cleanup_test_runs()


@pytest.fixture
def service(clean_decision_service_state):
    """Create a DecisionService instance."""
    return DecisionService()


def _cleanup_test_runs() -> None:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id FROM runs WHERE name LIKE ?",
        (f"{TEST_RUN_NAME_PREFIX}%",),
    ).fetchall()
    run_ids = [row["id"] for row in rows]
    for run_id in run_ids:
        for table in (
            "decision_results",
            "metrics_snapshots",
            "pair_results",
            "trade_summaries",
            "run_logs",
            "audit_logs",
            "artifacts",
            "run_stages",
        ):
            conn.execute(f"DELETE FROM {table} WHERE run_id = ?", (run_id,))
        conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        artifact_dir = settings.project_root / "artifacts" / "runs" / run_id
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir)
    conn.commit()
    conn.close()


def create_run(**overrides) -> dict:
    """Create a test run."""
    data = {
        "name": f"{TEST_RUN_NAME_PREFIX} Run",
        "mode": "manual_test",
        "timeframe": "1h",
        "risk_profile": "balanced",
    }
    data.update(overrides)
    return RunRepository().create_run(RunCreate(**data), create_default_stages=False)


def seed_parsed_results(
    run_id: str,
    *,
    trade_count: int = 80,
    profit_factor: float = 1.12,
    expectancy: float = 0.01,
    max_drawdown: float = 28.0,
    win_rate: float = 0.45,
    wins: int = 36,
    losses: int = 44,
    pair_profits: tuple[float, ...] = (60.0, 40.0),
) -> None:
    """Seed Part 05-style parsed rows."""
    metrics_repo = MetricsRepository()
    metrics_repo.create_metric_snapshot(
        MetricSnapshotCreate(
            run_id=run_id,
            stage_key="backtest_result_parse",
            net_profit=sum(pair_profits),
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            expectancy=expectancy,
            raw_json={"source": "test"},
        )
    )
    for index, profit in enumerate(pair_profits, start=1):
        metrics_repo.create_pair_result(
            PairResultCreate(
                run_id=run_id,
                pair=f"PAIR{index}/USDT",
                net_profit=profit,
                trade_count=max(1, trade_count // len(pair_profits)),
            )
        )
    metrics_repo.create_trade_summary(
        TradeSummaryCreate(
            run_id=run_id,
            total_trades=trade_count,
            wins=wins,
            losses=losses,
            draws=0,
        )
    )


def test_missing_run_returns_controlled_failure(service):
    """Missing runs do not raise; they return a controlled failure."""
    response = service.evaluate_run(
        DecisionEvaluationRequest(run_id="missing-run", apply_to_run=True)
    )

    assert response.success is False
    assert "run_not_found" in response.errors
    assert response.run_updated is False


def test_missing_parsed_metrics_returns_controlled_failure(service):
    """Runs without parsed metrics tell the caller to run Part 05 first."""
    run = create_run()

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))

    assert response.success is False
    assert "parsed_metrics_missing" in response.errors
    assert "Run the Part 05 parse endpoint or script first." in response.next_actions


def test_weak_negative_metrics_rejected_and_saved(service):
    """Weak parsed metrics are rejected and persisted."""
    run = create_run()
    seed_parsed_results(
        run["id"],
        trade_count=8678,
        profit_factor=0.44620083091599505,
        expectancy=-1.1478992387900437,
        max_drawdown=99.61469594219984,
        win_rate=0.19797188292233234,
        wins=1718,
        losses=6960,
        pair_profits=(-9961.46959422,),
    )

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))

    assert response.success is True
    assert response.classification == "rejected"
    assert response.saved_decision_id is not None
    assert "negative_expectancy" in response.blocking_failures
    latest = DecisionRepository().get_latest_decision_for_run(run["id"])
    assert latest["classification"] == "rejected"


@pytest.mark.parametrize(
    ("profit_factor", "expectancy", "max_drawdown", "expected"),
    [
        (1.12, 0.01, 28.0, "candidate"),
        (1.30, 0.04, 22.0, "promising"),
        (1.45, 0.10, 15.0, "validated"),
    ],
)
def test_strong_metrics_classify_by_thresholds(
    service,
    profit_factor,
    expectancy,
    max_drawdown,
    expected,
):
    """Positive parsed metrics classify according to thresholds."""
    run = create_run()
    seed_parsed_results(
        run["id"],
        profit_factor=profit_factor,
        expectancy=expectancy,
        max_drawdown=max_drawdown,
    )

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))

    assert response.success is True
    assert response.classification == expected


def test_decision_artifact_written_and_registered(service):
    """Evaluation writes and registers decision_result.json."""
    run = create_run()
    seed_parsed_results(run["id"])

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))

    assert response.decision_report_path == (
        f"artifacts/runs/{run['id']}/decisions/decision_result.json"
    )
    artifact_path = settings.project_root / response.decision_report_path
    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["classification"] == response.classification

    artifacts = ArtifactRepository().list_artifacts(run_id=run["id"])
    decision_artifacts = [
        artifact for artifact in artifacts if artifact["description"] == "Decision engine result"
    ]
    assert len(decision_artifacts) == 1
    assert decision_artifacts[0]["artifact_type"] == "metrics_json"


def test_run_classification_updated_when_apply_to_run_true(service):
    """apply_to_run=true writes the safe Part 06 classification to the run."""
    run = create_run()
    seed_parsed_results(run["id"], profit_factor=1.30, expectancy=0.04, max_drawdown=22.0)

    response = service.evaluate_run(
        DecisionEvaluationRequest(run_id=run["id"], apply_to_run=True)
    )

    assert response.run_updated is True
    updated = RunRepository().get_run(run["id"])
    assert updated["classification"] == "promising"
    assert updated["status"] == "created"


def test_run_not_updated_when_apply_to_run_false(service):
    """apply_to_run=false persists the decision without changing the run."""
    run = create_run()
    seed_parsed_results(run["id"], profit_factor=1.30, expectancy=0.04, max_drawdown=22.0)

    response = service.evaluate_run(
        DecisionEvaluationRequest(run_id=run["id"], apply_to_run=False)
    )

    assert response.run_updated is False
    updated = RunRepository().get_run(run["id"])
    assert updated["classification"] is None


def test_approved_and_exported_never_used(service):
    """Decision service never emits later lifecycle outcomes."""
    run = create_run()
    seed_parsed_results(run["id"], profit_factor=1.45, expectancy=0.10, max_drawdown=15.0)

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))
    payload = response.model_dump(mode="json")

    assert response.classification == "validated"
    assert payload["classification"] not in {"approved", "exported"}
    assert "approved" not in json.dumps(payload).lower()
    assert "exported" not in json.dumps(payload).lower()


def test_logs_and_audit_created(service):
    """Decision evaluation creates run logs and audit evidence."""
    run = create_run()
    seed_parsed_results(run["id"])

    response = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))

    logs = RunLogRepository().list_logs(run_id=run["id"], limit=20)
    messages = {log["message"] for log in logs}
    assert "decision_evaluation_started" in messages
    assert "decision_evaluation_completed" in messages

    audits = AuditLogRepository().list_audit_logs(
        run_id=run["id"],
        action_type="decision_evaluation",
    )
    assert len(audits) == 1
    assert audits[0]["actor"] == "system"
    assert audits[0]["approved"] is False
    assert audits[0]["after"]["classification"] == response.classification


def test_force_re_evaluation_works(service):
    """force=true deletes prior decision rows and overwrites report safely."""
    run = create_run()
    seed_parsed_results(run["id"])

    first = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"]))
    second = service.evaluate_run(DecisionEvaluationRequest(run_id=run["id"], force=True))

    assert first.success is True
    assert second.success is True
    decisions = DecisionRepository().list_decisions_for_run(run["id"])
    assert len(decisions) == 1
    assert decisions[0]["id"] == second.saved_decision_id
    assert Path(settings.project_root / second.decision_report_path).exists()
