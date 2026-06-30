"""
Tests for Part 11 strategy workspace schemas and safe static utilities.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.core.config import settings
from app.schemas.strategies import StrategyReadiness
from app.services.strategy_workspace_utils import (
    StrategyWorkspaceError,
    StrategyWorkspaceUtils,
)


VALID_STRATEGY_SOURCE = """
from freqtrade.strategy import IStrategy


class TestStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    minimal_roi = {"0": 0.1}
    stoploss = -0.1
    trailing_stop = True
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
def strategy_workspace(monkeypatch):
    project_root = Path(settings.project_root).resolve()
    user_data_dir = project_root / ".pytest_runtime" / "strategy-workspace-utils" / "user_data"
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


@pytest.fixture
def utils(strategy_workspace):
    return StrategyWorkspaceUtils()


def write_valid_strategy(strategies_dir: Path, name: str = "TestStrategy") -> Path:
    source = VALID_STRATEGY_SOURCE.replace("TestStrategy", name)
    path = strategies_dir / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return path


def write_valid_sidecar(strategies_dir: Path, name: str = "TestStrategy") -> Path:
    path = strategies_dir / f"{name}.json"
    path.write_text(
        json.dumps(
            {
                "buy": {"buy_rsi": 30, "api_key": "do-not-expose"},
                "sell": {"sell_rsi": 70},
                "roi": {"0": 0.1},
                "stoploss": -0.1,
                "trailing": {"trailing_stop": True},
                "protection": [],
                "max_open_trades": 3,
                "timeframe": "5m",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_safe_path_prevents_traversal(utils):
    with pytest.raises(StrategyWorkspaceError, match="traversal"):
        utils.resolve_project_relative_path("../freqtrade_workspace/user_data/strategies/TestStrategy.py")


def test_absolute_path_blocked(utils):
    with pytest.raises(StrategyWorkspaceError, match="project-relative"):
        utils.resolve_project_relative_path("/tmp/TestStrategy.py")


def test_non_py_json_extension_blocked(utils, strategy_workspace):
    txt_path = strategy_workspace / "TestStrategy.txt"
    txt_path.write_text("not allowed", encoding="utf-8")
    relative_path = utils.project_relative_path(txt_path)

    with pytest.raises(StrategyWorkspaceError, match=".py and .json"):
        utils.resolve_project_relative_path(relative_path)


def test_valid_strategy_summary_created(utils, strategy_workspace):
    write_valid_strategy(strategy_workspace)
    write_valid_sidecar(strategy_workspace)

    detail = utils.build_strategy_detail("TestStrategy")

    assert detail.readiness == StrategyReadiness.READY
    assert detail.strategy_file_path.endswith("TestStrategy.py")
    assert detail.sidecar_json_path.endswith("TestStrategy.json")
    assert detail.has_sidecar is True
    assert detail.syntax_valid is True
    assert detail.class_name == "TestStrategy"
    assert detail.metadata["timeframe"] == "5m"
    assert detail.metadata["can_short"] is False
    assert detail.metadata["has_minimal_roi"] is True
    assert detail.metadata["has_stoploss"] is True
    assert detail.metadata["has_trailing_fields"] is True
    assert detail.metadata["has_buy_params"] is True
    assert detail.metadata["has_sell_params"] is True
    assert detail.static_checks["has_populate_indicators"] is True
    assert detail.static_checks["has_entry_method"] is True
    assert detail.static_checks["has_exit_method"] is True
    assert detail.params_summary.parse_success is True
    assert "buy" in detail.params_summary.sections_present


def test_missing_sidecar_returns_missing_sidecar(utils, strategy_workspace):
    write_valid_strategy(strategy_workspace)

    detail = utils.build_strategy_detail("TestStrategy")

    assert detail.readiness == StrategyReadiness.MISSING_SIDECAR
    assert detail.has_sidecar is False
    assert any(issue.code == "sidecar_missing" for issue in detail.issues)
    assert "sidecar" in " ".join(detail.warnings).lower()


def test_malformed_json_returns_parse_error_issue(utils, strategy_workspace):
    write_valid_strategy(strategy_workspace)
    (strategy_workspace / "TestStrategy.json").write_text('{"buy": ', encoding="utf-8")

    detail = utils.build_strategy_detail("TestStrategy")

    assert detail.readiness == StrategyReadiness.PARSE_ERROR
    assert detail.params_summary.parse_success is False
    assert any(issue.code == "sidecar_parse_error" for issue in detail.issues)


def test_invalid_python_syntax_returns_parse_error(utils, strategy_workspace):
    (strategy_workspace / "TestStrategy.py").write_text(
        "class TestStrategy(IStrategy):\n    def broken(:\n        pass\n",
        encoding="utf-8",
    )
    write_valid_sidecar(strategy_workspace)

    detail = utils.build_strategy_detail("TestStrategy")

    assert detail.readiness == StrategyReadiness.PARSE_ERROR
    assert detail.syntax_valid is False
    assert any(issue.code == "python_syntax_error" for issue in detail.issues)


def test_strategy_file_is_not_executed(utils, strategy_workspace):
    marker_path = strategy_workspace / "executed-marker.txt"
    source = f"""
from pathlib import Path
Path({str(marker_path)!r}).write_text("executed", encoding="utf-8")

{VALID_STRATEGY_SOURCE}
"""
    (strategy_workspace / "TestStrategy.py").write_text(source, encoding="utf-8")
    write_valid_sidecar(strategy_workspace)

    detail = utils.build_strategy_detail("TestStrategy")

    assert detail.readiness == StrategyReadiness.READY
    assert marker_path.exists() is False


def test_params_summary_redacts_secret_like_values(utils, strategy_workspace):
    write_valid_strategy(strategy_workspace)
    write_valid_sidecar(strategy_workspace)

    summary = utils.parse_params_summary("TestStrategy")
    serialized = json.dumps(summary.model_dump(mode="json"))

    assert "do-not-expose" not in serialized
    assert "[REDACTED]" in serialized
