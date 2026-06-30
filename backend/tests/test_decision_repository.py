"""
Tests for DecisionRepository.
"""
import json

import pytest

from app.db.migrations import run_migrations
from app.db.sqlite import get_connection
from app.repositories.decisions import DecisionRepository
from app.schemas.decisions import (
    DecisionEvidence,
    DecisionGateResult,
    DecisionReason,
    DecisionResult,
)


@pytest.fixture
def decision_repo():
    """Create a DecisionRepository instance."""
    run_migrations()
    return DecisionRepository()


@pytest.fixture
def clean_decisions():
    """Clean decision_results before and after each test."""
    run_migrations()
    conn = get_connection()
    conn.execute("DELETE FROM decision_results")
    conn.commit()
    conn.close()
    yield
    conn = get_connection()
    conn.execute("DELETE FROM decision_results")
    conn.commit()
    conn.close()


def _decision_result(run_id: str = "run-123", created_at: str | None = None) -> DecisionResult:
    return DecisionResult(
        run_id=run_id,
        classification="rejected",
        confidence_score=18.0,
        policy_name="default_balanced",
        risk_profile="moderate",
        timeframe="1h",
        gates=[
            DecisionGateResult(
                gate_name="expectancy_positive",
                status="failed",
                actual_value=-1.14,
                threshold_value=0,
                message="Expectancy is not positive.",
                severity="blocking",
                details={"source": "metrics_snapshot"},
            )
        ],
        reasons=[
            DecisionReason(
                code="negative_expectancy",
                severity="blocking",
                message="Parsed expectancy is negative.",
                metric="expectancy",
                actual_value=-1.14,
                threshold_value=0,
                details={"source": "trade_level"},
            )
        ],
        evidence=DecisionEvidence(
            run_id=run_id,
            metrics_snapshot_id="metrics-123",
            trade_summary_id="summary-123",
            pair_count=1,
            trade_count=8678,
            profit_factor=0.4462,
            expectancy=-1.1479,
            max_drawdown=99.61,
            win_rate=0.1979,
            quality_flags=["negative_expectancy", "high_drawdown"],
            normalized_result_artifact_path=(
                "artifacts/runs/run-123/normalized/backtest_result.normalized.json"
            ),
        ),
        warnings=["single_pair_dependency"],
        blocking_failures=["negative_expectancy"],
        next_actions=["Review failed gates before repair."],
        created_at=created_at,
    )


class TestDecisionRepository:
    """Test decision result persistence."""

    def test_table_exists_after_migration(self, clean_decisions):
        conn = get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
            ("decision_results",),
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["name"] == "decision_results"

    def test_create_decision_result(self, decision_repo, clean_decisions):
        decision = decision_repo.create_decision_result(_decision_result())

        assert decision["id"] is not None
        assert decision["run_id"] == "run-123"
        assert decision["classification"] == "rejected"
        assert decision["confidence_score"] == 18.0
        assert decision["policy_name"] == "default_balanced"
        assert decision["evidence"]["trade_count"] == 8678

    def test_get_decision_result_by_id(self, decision_repo, clean_decisions):
        created = decision_repo.create_decision_result(_decision_result())

        fetched = decision_repo.get_decision_result(created["id"])

        assert fetched is not None
        assert fetched["id"] == created["id"]
        assert fetched["gates"][0]["gate_name"] == "expectancy_positive"
        assert fetched["reasons"][0]["code"] == "negative_expectancy"

    def test_get_latest_decision_for_run(self, decision_repo, clean_decisions):
        decision_repo.create_decision_result(
            _decision_result(created_at="2026-06-28T10:00:00+00:00")
        )
        latest_created = decision_repo.create_decision_result(
            _decision_result(created_at="2026-06-28T11:00:00+00:00")
        )

        latest = decision_repo.get_latest_decision_for_run("run-123")

        assert latest is not None
        assert latest["id"] == latest_created["id"]
        assert latest["created_at"] == "2026-06-28T11:00:00+00:00"

    def test_list_decisions_for_run(self, decision_repo, clean_decisions):
        decision_repo.create_decision_result(
            _decision_result(created_at="2026-06-28T10:00:00+00:00")
        )
        decision_repo.create_decision_result(
            _decision_result(created_at="2026-06-28T11:00:00+00:00")
        )
        decision_repo.create_decision_result(
            _decision_result(run_id="other-run", created_at="2026-06-28T12:00:00+00:00")
        )

        decisions = decision_repo.list_decisions_for_run("run-123")

        assert len(decisions) == 2
        assert decisions[0]["created_at"] == "2026-06-28T11:00:00+00:00"

    def test_delete_decisions_for_run(self, decision_repo, clean_decisions):
        decision_repo.create_decision_result(_decision_result())
        decision_repo.create_decision_result(_decision_result(run_id="other-run"))

        deleted_count = decision_repo.delete_decisions_for_run("run-123")

        assert deleted_count == 1
        assert decision_repo.get_latest_decision_for_run("run-123") is None
        assert decision_repo.get_latest_decision_for_run("other-run") is not None

    def test_json_fields_round_trip(self, decision_repo, clean_decisions):
        created = decision_repo.create_decision_result(_decision_result())
        fetched = decision_repo.get_decision_result(created["id"])

        assert fetched["gates"] == created["gates"]
        assert fetched["reasons"] == created["reasons"]
        assert fetched["evidence"] == created["evidence"]
        assert fetched["warnings"] == ["single_pair_dependency"]
        assert fetched["blocking_failures"] == ["negative_expectancy"]
        assert fetched["next_actions"] == ["Review failed gates before repair."]

    def test_invalid_classification_rejected(self, decision_repo, clean_decisions):
        result = _decision_result()
        result.classification = "approved"

        with pytest.raises(ValueError, match="Invalid decision classification"):
            decision_repo.create_decision_result(result)

    def test_no_secrets_in_serialized_json(self, decision_repo, clean_decisions):
        result = _decision_result()
        result.gates[0].details["api_key"] = "super-secret-key"
        result.reasons[0].details["nested"] = {"token": "super-secret-token"}

        created = decision_repo.create_decision_result(result)
        serialized = decision_repo.serialize_decision(result)

        assert "super-secret" not in json.dumps(serialized)
        assert created["gates"][0]["details"]["api_key"] == "[REDACTED]"
        assert created["reasons"][0]["details"]["nested"]["token"] == "[REDACTED]"

        conn = get_connection()
        row = conn.execute(
            "SELECT decision_json, gates_json, reasons_json FROM decision_results WHERE id = ?",
            (created["id"],),
        ).fetchone()
        conn.close()

        stored_json = json.dumps(dict(row))
        assert "super-secret" not in stored_json
        assert "[REDACTED]" in stored_json
