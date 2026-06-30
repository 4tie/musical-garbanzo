"""
Tests for Part 06 Decisions API endpoints.
"""
from __future__ import annotations

import json
import shutil

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.db.migrations import run_migrations
from app.db.sqlite import get_connection
from app.main import app
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import MetricSnapshotCreate, PairResultCreate, TradeSummaryCreate


TEST_RUN_NAME_PREFIX = "Decision API Test"


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def clean_decision_api_state():
    """Clean rows and artifacts created by these tests."""
    run_migrations()
    _cleanup_test_runs()
    yield
    _cleanup_test_runs()


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
        shutil.rmtree(settings.project_root / "artifacts" / "runs" / run_id, ignore_errors=True)
    conn.commit()
    conn.close()


async def create_run(client, **overrides) -> dict:
    """Create a run through the public API."""
    data = {
        "name": f"{TEST_RUN_NAME_PREFIX} Run",
        "mode": "manual_test",
        "timeframe": "1h",
        "risk_profile": "balanced",
    }
    data.update(overrides)
    response = await client.post("/api/runs", json=data)
    assert response.status_code == 201
    return response.json()


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
    """Seed parsed Part 05 evidence rows."""
    repo = MetricsRepository()
    repo.create_metric_snapshot(
        MetricSnapshotCreate(
            run_id=run_id,
            stage_key="backtest_result_parse",
            net_profit=sum(pair_profits),
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trade_count=trade_count,
            expectancy=expectancy,
            raw_json={"source": "decision-api-test", "api_key": "super-secret"},
        )
    )
    for index, profit in enumerate(pair_profits, start=1):
        repo.create_pair_result(
            PairResultCreate(
                run_id=run_id,
                pair=f"PAIR{index}/USDT",
                net_profit=profit,
                trade_count=max(1, trade_count // len(pair_profits)),
            )
        )
    repo.create_trade_summary(
        TradeSummaryCreate(
            run_id=run_id,
            total_trades=trade_count,
            wins=wins,
            losses=losses,
            draws=0,
        )
    )


async def test_policies_endpoint(client, clean_decision_api_state):
    """Policies endpoint returns available policy summaries."""
    response = await client.get("/api/decisions/policies")
    v1_response = await client.get("/api/v1/decisions/policies")

    assert response.status_code == 200
    assert v1_response.status_code == 200
    names = {policy["policy_name"] for policy in response.json()}
    assert {"default_conservative", "default_balanced", "default_aggressive"}.issubset(names)


async def test_policy_detail_endpoint(client, clean_decision_api_state):
    """Policy detail endpoint returns thresholds."""
    response = await client.get("/api/decisions/policies/default_balanced")

    assert response.status_code == 200
    data = response.json()
    assert data["policy_name"] == "default_balanced"
    assert data["thresholds"]["candidate_profit_factor"] == 1.10


async def test_policy_not_found_clean_error(client, clean_decision_api_state):
    """Unknown policies return a clean 404."""
    response = await client.get("/api/decisions/policies/nope")

    assert response.status_code == 404
    assert response.json()["type"] == "not_found"


async def test_evaluate_missing_run_returns_404(client, clean_decision_api_state):
    """Evaluating a missing run returns clean 404."""
    response = await client.post("/api/decisions/runs/missing-run/evaluate", json={})

    assert response.status_code == 404
    assert response.json()["type"] == "not_found"


async def test_evaluate_missing_parsed_metrics_controlled_failure(client, clean_decision_api_state):
    """Runs without parsed metrics return success=false."""
    run = await create_run(client)

    response = await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "parsed_metrics_missing" in data["errors"]
    assert data["run_updated"] is False


async def test_evaluate_parsed_losing_result_rejected(client, clean_decision_api_state):
    """Parsed losing evidence evaluates to rejected."""
    run = await create_run(client)
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

    response = await client.post(
        f"/api/decisions/runs/{run['id']}/evaluate",
        json={"apply_to_run": True, "api_key": "super-secret"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["classification"] == "rejected"
    assert data["saved_decision_id"] is not None
    assert "negative_expectancy" in data["blocking_failures"]


async def test_latest_decision_endpoint(client, clean_decision_api_state):
    """Latest decision endpoint returns saved decision."""
    run = await create_run(client)
    seed_parsed_results(run["id"])
    evaluate = await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})

    response = await client.get(f"/api/decisions/runs/{run['id']}/latest")

    assert response.status_code == 200
    assert response.json()["id"] == evaluate.json()["saved_decision_id"]


async def test_all_decisions_endpoint(client, clean_decision_api_state):
    """All decisions endpoint lists saved decisions for a run."""
    run = await create_run(client)
    seed_parsed_results(run["id"])
    await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})
    await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})

    response = await client.get(f"/api/decisions/runs/{run['id']}")

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_compatibility_endpoints(client, clean_decision_api_state):
    """Results and runs compatibility endpoints return latest decision."""
    run = await create_run(client)
    seed_parsed_results(run["id"])
    await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})

    results_response = await client.get(f"/api/results/backtest/{run['id']}/decision")
    runs_response = await client.get(f"/api/runs/{run['id']}/decision")

    assert results_response.status_code == 200
    assert runs_response.status_code == 200
    assert results_response.json()["run_id"] == run["id"]
    assert runs_response.json()["run_id"] == run["id"]


async def test_decision_not_found_clean_error(client, clean_decision_api_state):
    """Latest decision endpoint returns clean 404 before evaluation."""
    run = await create_run(client)

    response = await client.get(f"/api/decisions/runs/{run['id']}/latest")

    assert response.status_code == 404
    assert response.json()["type"] == "not_found"


async def test_openapi_includes_decisions_tag(client, clean_decision_api_state):
    """OpenAPI includes Decisions-tagged endpoints."""
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    operation = response.json()["paths"]["/api/decisions/policies"]["get"]
    assert "Decisions" in operation["tags"]


async def test_no_approved_export_live_wording_in_decision_response(client, clean_decision_api_state):
    """Decision API responses avoid deployment-oriented wording."""
    run = await create_run(client)
    seed_parsed_results(run["id"], profit_factor=1.45, expectancy=0.10, max_drawdown=15.0)

    response = await client.post(f"/api/decisions/runs/{run['id']}/evaluate", json={})

    body = json.dumps(response.json()).lower()
    assert response.json()["classification"] == "validated"
    assert "approved" not in body
    assert "export" not in body
    assert "live" not in body


async def test_no_secrets_exposed(client, clean_decision_api_state):
    """Decision endpoints do not echo secret-like values."""
    run = await create_run(client)
    seed_parsed_results(run["id"])

    evaluate = await client.post(
        f"/api/decisions/runs/{run['id']}/evaluate",
        json={"api_key": "super-secret", "token": "super-secret-token"},
    )
    latest = await client.get(f"/api/decisions/runs/{run['id']}/latest")
    policies = await client.get("/api/decisions/policies")

    body = json.dumps([evaluate.json(), latest.json(), policies.json()]).lower()
    assert "super-secret" not in body
    assert "api_key" not in body
    assert "token" not in body
