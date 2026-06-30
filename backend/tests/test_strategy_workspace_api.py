"""
Tests for Part 11 strategy workspace API endpoints.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import httpx
import pytest
from httpx import ASGITransport

from app.core.config import settings
from app.main import app


VALID_STRATEGY_SOURCE = """
from freqtrade.strategy import IStrategy


class TestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    minimal_roi = {"0": 0.1}
    stoploss = -0.1
    buy_params = {"buy_rsi": 30}
    sell_params = {"sell_rsi": 70}

    def populate_indicators(self, dataframe, metadata):
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        return dataframe
"""


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def strategy_workspace(monkeypatch):
    project_root = Path(settings.project_root).resolve()
    user_data_dir = project_root / ".pytest_runtime" / "strategy-workspace-api" / "user_data"
    strategies_dir = user_data_dir / "strategies"
    shutil.rmtree(user_data_dir.parent, ignore_errors=True)
    strategies_dir.mkdir(parents=True)

    monkeypatch.setattr(
        settings,
        "FREQTRADE_USER_DATA_DIR",
        str(user_data_dir.relative_to(project_root)),
    )

    yield strategies_dir

    shutil.rmtree(user_data_dir.parent, ignore_errors=True)


def write_strategy(strategies_dir: Path, name: str = "TestStrategy", source: str | None = None) -> None:
    strategy_source = (source or VALID_STRATEGY_SOURCE).replace("TestStrategy", name)
    (strategies_dir / f"{name}.py").write_text(strategy_source, encoding="utf-8")


def write_sidecar(strategies_dir: Path, name: str = "TestStrategy", payload: dict | None = None) -> None:
    (strategies_dir / f"{name}.json").write_text(
        json.dumps(
            payload
            or {
                "buy": {"buy_rsi": 30},
                "sell": {"sell_rsi": 70},
                "roi": {"0": 0.1},
                "stoploss": -0.1,
                "timeframe": "5m",
            }
        ),
        encoding="utf-8",
    )


async def test_list_strategies(client, strategy_workspace):
    write_strategy(strategy_workspace, "TestStrategy")
    write_sidecar(strategy_workspace, "TestStrategy")
    write_strategy(strategy_workspace, "MissingSidecar")

    response = await client.get("/api/strategies")

    assert response.status_code == 200
    data = response.json()
    assert [strategy["strategy_name"] for strategy in data] == ["MissingSidecar", "TestStrategy"]
    assert all(not strategy["strategy_file_path"].startswith("/") for strategy in data)


async def test_list_strategies_filters(client, strategy_workspace):
    write_strategy(strategy_workspace, "ReadyStrategy")
    write_sidecar(strategy_workspace, "ReadyStrategy")
    write_strategy(strategy_workspace, "MissingSidecar")

    response = await client.get(
        "/api/strategies",
        params={
            "readiness": "ready",
            "has_sidecar": "true",
            "search": "ready",
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["strategy_name"] == "ReadyStrategy"
    assert data[0]["readiness"] == "ready"


async def test_get_detail(client, strategy_workspace):
    write_strategy(strategy_workspace, "TestStrategy")
    write_sidecar(strategy_workspace, "TestStrategy")

    response = await client.get("/api/strategies/TestStrategy")

    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "TestStrategy"
    assert data["readiness"] == "ready"
    assert data["syntax_valid"] is True
    assert data["class_name"] == "TestStrategy"
    assert not data["strategy_file_path"].startswith("/")
    assert not data["sidecar_json_path"].startswith("/")


async def test_get_missing_strategy_returns_404(client, strategy_workspace):
    response = await client.get("/api/strategies/MissingStrategy")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] is True
    assert "not found" in data["message"].lower()


async def test_get_params(client, strategy_workspace):
    write_strategy(strategy_workspace, "TestStrategy")
    write_sidecar(strategy_workspace, "TestStrategy")

    response = await client.get("/api/strategies/TestStrategy/params")

    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "TestStrategy"
    assert data["parse_success"] is True
    assert "buy" in data["sections_present"]
    assert not data["sidecar_json_path"].startswith("/")


async def test_missing_sidecar_params_payload(client, strategy_workspace):
    write_strategy(strategy_workspace, "TestStrategy")

    response = await client.get("/api/strategies/TestStrategy/params")

    assert response.status_code == 200
    data = response.json()
    assert data["exists"] is False
    assert data["parse_success"] is False
    assert any(issue["code"] == "sidecar_missing" for issue in data["issues"])


async def test_validate_endpoint(client, strategy_workspace):
    write_strategy(strategy_workspace, "TestStrategy")
    write_sidecar(strategy_workspace, "TestStrategy")

    response = await client.post("/api/strategies/TestStrategy/validate")

    assert response.status_code == 200
    data = response.json()
    assert data["strategy_name"] == "TestStrategy"
    assert data["readiness"] == "ready"


async def test_unsafe_name_blocked(client, strategy_workspace):
    response = await client.get("/api/strategies/Invalid%20Name")

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "unsafe" in data["message"].lower() or "invalid" in data["message"].lower()
