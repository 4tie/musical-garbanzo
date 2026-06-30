"""
Tests for Part 11 safe strategy import API.
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


class ImportedStrategy(IStrategy):
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
def import_workspace(monkeypatch):
    project_root = Path(settings.project_root).resolve()
    root = project_root / ".pytest_runtime" / "strategy-import-api"
    source_dir = root / "sources"
    user_data_dir = root / "user_data"
    strategies_dir = user_data_dir / "strategies"
    shutil.rmtree(root, ignore_errors=True)
    source_dir.mkdir(parents=True)
    strategies_dir.mkdir(parents=True)

    monkeypatch.setattr(
        settings,
        "FREQTRADE_USER_DATA_DIR",
        str(user_data_dir.relative_to(project_root)),
    )

    yield {
        "project_root": project_root,
        "root": root,
        "source_dir": source_dir,
        "strategies_dir": strategies_dir,
    }

    shutil.rmtree(root, ignore_errors=True)


def relative(project_root: Path, path: Path) -> str:
    return path.resolve().relative_to(project_root).as_posix()


def write_source_strategy(import_workspace, name: str = "ImportedStrategy", source: str | None = None) -> Path:
    source_text = (source or VALID_STRATEGY_SOURCE).replace("ImportedStrategy", name)
    path = import_workspace["source_dir"] / f"{name}.py"
    path.write_text(source_text, encoding="utf-8")
    return path


def write_source_sidecar(import_workspace, name: str = "ImportedStrategy", payload: dict | None = None) -> Path:
    path = import_workspace["source_dir"] / f"{name}.json"
    path.write_text(
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
    return path


async def test_valid_py_import(client, import_workspace):
    source_path = write_source_strategy(import_workspace)

    response = await client.post(
        "/api/strategies/import",
        json={"source_path": relative(import_workspace["project_root"], source_path)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported"] is True
    assert data["strategy_name"] == "ImportedStrategy"
    assert data["readiness"] == "missing_sidecar"
    assert (import_workspace["strategies_dir"] / "ImportedStrategy.py").exists()


async def test_valid_py_and_json_import(client, import_workspace):
    source_path = write_source_strategy(import_workspace)
    sidecar_path = write_source_sidecar(import_workspace)

    response = await client.post(
        "/api/strategies/import",
        json={
            "source_path": relative(import_workspace["project_root"], source_path),
            "sidecar_source_path": relative(import_workspace["project_root"], sidecar_path),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported"] is True
    assert data["readiness"] == "ready"
    assert data["sidecar_json_path"].endswith("ImportedStrategy.json")
    assert (import_workspace["strategies_dir"] / "ImportedStrategy.py").exists()
    assert (import_workspace["strategies_dir"] / "ImportedStrategy.json").exists()


async def test_invalid_extension_rejected(client, import_workspace):
    source_path = import_workspace["source_dir"] / "ImportedStrategy.txt"
    source_path.write_text(VALID_STRATEGY_SOURCE, encoding="utf-8")

    response = await client.post(
        "/api/strategies/import",
        json={"source_path": relative(import_workspace["project_root"], source_path)},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert ".py" in data["message"]


async def test_path_traversal_rejected(client, import_workspace):
    response = await client.post(
        "/api/strategies/import",
        json={"source_path": "../outside/ImportedStrategy.py"},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "source_path" in str(data).lower()


async def test_overwrite_conflict_returns_controlled_response(client, import_workspace):
    source_path = write_source_strategy(import_workspace)
    (import_workspace["strategies_dir"] / "ImportedStrategy.py").write_text(
        "# existing strategy\n",
        encoding="utf-8",
    )

    response = await client.post(
        "/api/strategies/import",
        json={
            "source_path": relative(import_workspace["project_root"], source_path),
            "overwrite_confirmed": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["conflict"] is True
    assert data["imported"] is False
    assert "strategy_file_path" in data["existing_files"]
    assert (import_workspace["strategies_dir"] / "ImportedStrategy.py").read_text(encoding="utf-8") == "# existing strategy\n"


async def test_orphan_sidecar_conflict_returns_controlled_response(client, import_workspace):
    source_path = write_source_strategy(import_workspace)
    (import_workspace["strategies_dir"] / "ImportedStrategy.json").write_text(
        json.dumps({"buy": {"existing": True}}),
        encoding="utf-8",
    )

    response = await client.post(
        "/api/strategies/import",
        json={"source_path": relative(import_workspace["project_root"], source_path)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["conflict"] is True
    assert data["imported"] is False
    assert "sidecar_json_path" in data["existing_files"]
    assert not (import_workspace["strategies_dir"] / "ImportedStrategy.py").exists()


async def test_malformed_sidecar_returns_issue(client, import_workspace):
    source_path = write_source_strategy(import_workspace)
    sidecar_path = import_workspace["source_dir"] / "ImportedStrategy.json"
    sidecar_path.write_text("{broken", encoding="utf-8")

    response = await client.post(
        "/api/strategies/import",
        json={
            "source_path": relative(import_workspace["project_root"], source_path),
            "sidecar_source_path": relative(import_workspace["project_root"], sidecar_path),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["imported"] is False
    assert data["readiness"] == "parse_error"
    assert any(issue["code"] == "sidecar_parse_error" for issue in data["issues"])
    assert not (import_workspace["strategies_dir"] / "ImportedStrategy.py").exists()


async def test_imported_strategy_is_not_executed(client, import_workspace):
    marker_path = import_workspace["root"] / "executed-marker.txt"
    source_path = write_source_strategy(
        import_workspace,
        source=f"""
from pathlib import Path
Path({str(marker_path)!r}).write_text("executed", encoding="utf-8")

{VALID_STRATEGY_SOURCE}
""",
    )

    response = await client.post(
        "/api/strategies/import",
        json={"source_path": relative(import_workspace["project_root"], source_path)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["imported"] is True
    assert marker_path.exists() is False
