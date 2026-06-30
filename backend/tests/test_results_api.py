"""
Tests for parsed backtest Results API endpoints.
"""
import json
import shutil
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.db.sqlite import get_connection
from app.main import app
from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import MetricSnapshotCreate, PairResultCreate, TradeSummaryCreate


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def clean_db_and_artifacts():
    """Clean parser-related tables and test artifacts before/after each test."""
    _clean_tables()
    yield
    _clean_tables()
    shutil.rmtree(settings.project_root / "artifacts" / "runs" / "api-test-run", ignore_errors=True)


def _clean_tables():
    """Delete rows touched by Results API tests."""
    conn = get_connection()
    for table in (
        "audit_logs",
        "run_logs",
        "artifacts",
        "trade_summaries",
        "pair_results",
        "metrics_snapshots",
        "run_stages",
        "runs",
    ):
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


async def create_run(client, run_id: str | None = None) -> str:
    """Create a run and optionally rename its ID for deterministic artifact paths."""
    response = await client.post(
        "/api/runs",
        json={"name": "Results API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
    )
    assert response.status_code == 201
    created_id = response.json()["id"]
    if run_id and run_id != created_id:
        conn = get_connection()
        conn.execute("UPDATE runs SET id = ? WHERE id = ?", (run_id, created_id))
        conn.execute("UPDATE run_stages SET run_id = ? WHERE run_id = ?", (run_id, created_id))
        conn.commit()
        conn.close()
        return run_id
    return created_id


def write_backtest_fixture(run_id: str = "api-test-run") -> Path:
    """Write a small raw backtest result fixture in the Part 04 artifact layout."""
    result_dir = (
        settings.project_root
        / "artifacts"
        / "runs"
        / run_id
        / "raw_freqtrade"
        / "backtest_results"
    )
    result_dir.mkdir(parents=True, exist_ok=True)
    result_file = result_dir / "backtest-result.json"
    result_file.write_text(
        json.dumps(
            {
                "strategy": {
                    "HERSmokeStrategy": {
                        "profit_total_abs": 10.0,
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
                                "profit_total_abs": 8.0,
                                "profit_factor": 1.6,
                                "max_drawdown": 4.0,
                                "wins": 1,
                                "losses": 1,
                                "draws": 0,
                            },
                            {
                                "pair": "ETH/USDT",
                                "trades": 1,
                                "profit_total_abs": 2.0,
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
        ),
        encoding="utf-8",
    )
    return result_file


async def test_parse_endpoint_missing_run_returns_404(client, clean_db_and_artifacts):
    """Parsing a non-existent run returns 404."""
    response = await client.post("/api/results/backtest/missing-run/parse", json={"force": False})

    assert response.status_code == 404


async def test_parse_endpoint_missing_outputs_returns_controlled_failure(client, clean_db_and_artifacts):
    """Existing run with no outputs returns controlled parse failure."""
    run_id = await create_run(client, "api-test-run")

    response = await client.post(f"/api/results/backtest/{run_id}/parse", json={"force": False})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert any(flag["code"] == "missing_backtest_file" for flag in data["quality_report"]["flags"])


async def test_parse_endpoint_succeeds_with_fixture_artifact(client, clean_db_and_artifacts):
    """Parse endpoint succeeds with a Part 04-style fixture file."""
    run_id = await create_run(client, "api-test-run")
    write_backtest_fixture(run_id)

    response = await client.post(f"/api/results/backtest/{run_id}/parse", json={"force": False})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metrics"]["metrics"]["profit_factor"] == 1.4
    assert data["normalized_result_path"].endswith("artifacts/runs/api-test-run/normalized/backtest_result.normalized.json")


async def test_combined_result_returns_latest_metrics(client, clean_db_and_artifacts):
    """Combined result endpoint returns latest metrics."""
    run_id = await create_run(client, "api-test-run")
    MetricsRepository().create_metric_snapshot(
        MetricSnapshotCreate(run_id=run_id, net_profit=11.0, raw_json={"source": "test"})
    )

    response = await client.get(f"/api/results/backtest/{run_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["latest_metrics"]["net_profit"] == 11.0


async def test_pair_results_endpoint_works(client, clean_db_and_artifacts):
    """Existing pair results endpoint remains available."""
    run_id = await create_run(client, "api-test-run")
    MetricsRepository().upsert_pair_result(
        PairResultCreate(run_id=run_id, pair="BTC/USDT", net_profit=5.0)
    )

    response = await client.get(f"/api/runs/{run_id}/pair-results")

    assert response.status_code == 200
    assert response.json()[0]["pair"] == "BTC/USDT"


async def test_trade_summary_endpoint_works(client, clean_db_and_artifacts):
    """Existing trade summary endpoint remains available."""
    run_id = await create_run(client, "api-test-run")
    MetricsRepository().replace_trade_summary(
        TradeSummaryCreate(run_id=run_id, total_trades=3, wins=2, losses=1, draws=0)
    )

    response = await client.get(f"/api/runs/{run_id}/trade-summary")

    assert response.status_code == 200
    assert response.json()["total_trades"] == 3


async def test_quality_endpoint_works(client, clean_db_and_artifacts):
    """Quality endpoint returns latest quality report after parsing."""
    run_id = await create_run(client, "api-test-run")
    write_backtest_fixture(run_id)
    await client.post(f"/api/results/backtest/{run_id}/parse", json={"force": False})

    response = await client.get(f"/api/results/backtest/{run_id}/quality")
    compatibility = await client.get(f"/api/runs/{run_id}/result-quality")

    assert response.status_code == 200
    assert compatibility.status_code == 200
    assert "flags" in response.json()


async def test_normalized_endpoint_404_if_missing(client, clean_db_and_artifacts):
    """Normalized endpoint returns 404 before artifact exists."""
    run_id = await create_run(client, "api-test-run")

    response = await client.get(f"/api/results/backtest/{run_id}/normalized")

    assert response.status_code == 404


async def test_normalized_endpoint_returns_artifact_if_present(client, clean_db_and_artifacts):
    """Normalized endpoint returns normalized artifact JSON after parsing."""
    run_id = await create_run(client, "api-test-run")
    write_backtest_fixture(run_id)
    await client.post(f"/api/results/backtest/{run_id}/parse", json={"force": False})

    response = await client.get(f"/api/results/backtest/{run_id}/normalized")

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["metrics"]["profit_factor"] == 1.4
    assert all(not str(path).startswith(str(settings.project_root)) for path in data["source_files"])


async def test_openapi_includes_results_tag(client, clean_db_and_artifacts):
    """OpenAPI includes Results-tagged endpoints."""
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    operations = response.json()["paths"]["/api/results/backtest/{run_id}/parse"]["post"]
    assert "Results" in operations["tags"]


async def test_no_secrets_exposed(client, clean_db_and_artifacts):
    """Results endpoints do not expose known secret names or .env content."""
    run_id = await create_run(client, "api-test-run")
    write_backtest_fixture(run_id)
    await client.post(f"/api/results/backtest/{run_id}/parse", json={"force": False})

    responses = [
        await client.get(f"/api/results/backtest/{run_id}"),
        await client.get(f"/api/results/backtest/{run_id}/quality"),
        await client.get(f"/api/results/backtest/{run_id}/normalized"),
        await client.get("/openapi.json"),
    ]
    text = json.dumps([response.json() for response in responses])

    assert "DISCORD_BOT_TOKEN" not in text
    assert "APP_SECRET_KEY" not in text
    assert ".env" not in text
